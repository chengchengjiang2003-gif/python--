import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app import main


class RelayAPI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = main.DATA_DIR
        main.DATA_DIR = Path(self.temp.name)
        main.rate_windows.clear()
        self.owner = TestClient(main.app)
        self.owner.__enter__()
        self.member = TestClient(main.app)
        self.member.__enter__()
        self.owner_user = self.register(self.owner, 'owner')
        self.member_user = self.register(self.member, 'member')
        self.pid = self.owner.get('/api/projects').json()[0]['id']

    def tearDown(self):
        self.member.__exit__(None, None, None)
        self.owner.__exit__(None, None, None)
        main.DATA_DIR = self.previous
        self.temp.cleanup()

    def register(self, client, name):
        response = client.post('/api/auth/register', json={'username': name, 'display_name': name, 'password': 'test-pass-123'})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['user']

    def join(self, role='contributor'):
        invite = self.owner.post(f'/api/projects/{self.pid}/invitations', json={'role': role})
        self.assertEqual(invite.status_code, 200)
        response = self.member.post('/api/invitations/join', json={'token': invite.json()['token']})
        self.assertEqual(response.status_code, 200)

    def project(self):
        return self.owner.get('/api/projects/'+self.pid).json()

    def test_password_login_logout_and_persistence(self):
        self.assertEqual(self.owner.post('/api/auth/logout').status_code, 200)
        self.assertEqual(self.owner.get('/api/me').status_code, 401)
        self.assertEqual(self.owner.post('/api/auth/login', json={'username': 'owner', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.owner.post('/api/auth/login', json={'username': 'owner', 'password': 'test-pass-123'}).status_code, 200)
        self.assertEqual(self.owner.get('/api/projects').json()[0]['id'], self.pid)

    def test_private_project_and_cross_site_rejection(self):
        self.assertEqual(self.member.get('/api/projects/'+self.pid).status_code, 403)
        response = self.owner.post(f'/api/projects/{self.pid}/messages', json={'content': 'cross site'}, headers={'Origin': 'https://attacker.example'})
        self.assertEqual(response.status_code, 403)

    def test_invite_revoke_and_remove_permissions(self):
        result = self.owner.post(f'/api/projects/{self.pid}/invitations', json={'role': 'contributor'}).json()
        self.owner.delete(f'/api/projects/{self.pid}/invitations')
        self.assertEqual(self.member.post('/api/invitations/join', json={'token': result['token']}).status_code, 400)
        self.join()
        self.assertEqual(self.member.get('/api/projects/'+self.pid).status_code, 200)
        self.assertEqual(self.owner.delete(f'/api/projects/{self.pid}/members/'+self.member_user['id']).status_code, 200)
        self.assertEqual(self.member.get('/api/projects/'+self.pid).status_code, 403)

    def test_observer_read_only(self):
        self.join('observer')
        self.assertEqual(self.member.get('/api/projects/'+self.pid).status_code, 200)
        self.assertEqual(self.member.post(f'/api/projects/{self.pid}/messages', json={'content': 'not allowed'}).status_code, 403)
        self.assertEqual(self.member.put(f'/api/projects/{self.pid}/document', json={'revision': 1, 'content': 'bad'}).status_code, 403)

    def test_document_conflict_does_not_overwrite(self):
        self.join()
        doc = self.project()['document']
        first = self.owner.put(f'/api/projects/{self.pid}/document', json={'revision': doc['revision'], 'content': 'owner revision'})
        self.assertEqual(first.status_code, 200)
        stale = self.member.put(f'/api/projects/{self.pid}/document', json={'revision': doc['revision'], 'content': 'stale member draft'})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['detail']['document']['content'], 'owner revision')
        self.assertEqual(self.project()['document']['content'], 'owner revision')

    def test_task_owner_and_idempotent_settlement(self):
        self.join()
        task = next(t for t in self.project()['tasks'] if t['status'] == 'review')
        body = {'revision': task['revision'], 'artifact_id': task['artifact']['id']}
        self.assertEqual(self.member.post('/api/tasks/'+task['id']+'/approve', json=body).status_code, 403)
        self.assertEqual(self.owner.post('/api/tasks/'+task['id']+'/approve', json=body).status_code, 200)
        self.assertEqual(self.owner.post('/api/tasks/'+task['id']+'/approve', json=body).status_code, 409)
        detail = self.project()
        self.assertEqual(len(detail['settlements']), 1)
        self.assertEqual(detail['totals']['paid'], 60*main.UNIT)

    def test_assign_submit_and_fixed_artifact(self):
        self.join()
        task = next(t for t in self.project()['tasks'] if t['status'] == 'todo')
        reassigned = self.owner.patch('/api/tasks/'+task['id'], json={'revision': task['revision'], 'assignee_id': self.member_user['id']})
        self.assertEqual(reassigned.status_code, 200)
        task = next(t for t in self.project()['tasks'] if t['id'] == task['id'])
        result = self.member.post('/api/tasks/'+task['id']+'/submit', json={'revision': task['revision'], 'content': 'This is a complete delivery with test notes.'})
        self.assertEqual(result.status_code, 200)
        saved = next(t for t in self.project()['tasks'] if t['id'] == task['id'])
        self.assertEqual(saved['artifact']['digest'], main.digest(saved['artifact']['content']))
        self.assertEqual(self.owner.delete(f'/api/projects/{self.pid}/members/'+self.member_user['id']).status_code, 409)

    def test_budget_constraints(self):
        self.join()
        data = {'title': 'extra task', 'criteria': 'clear standard', 'description': '', 'assignee_id': self.owner_user['id'], 'amount': '1'}
        self.assertEqual(self.owner.post(f'/api/projects/{self.pid}/tasks', json=data).status_code, 409)
        data['amount'] = 'NaN'
        self.assertEqual(self.owner.post(f'/api/projects/{self.pid}/tasks', json=data).status_code, 422)
        data['amount'] = '0.0000001'
        self.assertEqual(self.owner.post(f'/api/projects/{self.pid}/tasks', json=data).status_code, 422)
        data['assignee_id'] = self.member_user['id']
        data['amount'] = '1'
        self.assertEqual(self.member.post(f'/api/projects/{self.pid}/tasks', json=data).status_code, 403)

    def test_file_permissions_and_bytes(self):
        content = b'private project bytes'
        result = self.owner.post(f'/api/projects/{self.pid}/files', files={'file': ('notes.txt', content, 'text/plain')})
        self.assertEqual(result.status_code, 200, result.text)
        fid = result.json()['id']
        self.assertEqual(self.member.get('/api/files/'+fid).status_code, 403)
        self.join()
        self.assertEqual(self.member.get('/api/files/'+fid).content, content)
        oversized = self.owner.post(f'/api/projects/{self.pid}/files', files={'file': ('big', b'a'*(10*1024*1024+1))})
        self.assertEqual(oversized.status_code, 413)

    def test_wallet_signature_nonce_replay_and_binding(self):
        wallet = Account.create()
        challenge = self.owner.post('/api/wallet/challenge', json={'address': wallet.address, 'link': True}).json()
        signature = Account.sign_message(encode_defunct(text=challenge['message']), wallet.key).signature.hex()
        body = {'challenge_id': challenge['challenge_id'], 'signature': signature}
        result = self.owner.post('/api/wallet/verify', json=body)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['user']['wallet'], wallet.address.lower())
        self.assertEqual(self.owner.post('/api/wallet/verify', json=body).status_code, 400)
        self.owner.post('/api/auth/logout')
        challenge = self.owner.post('/api/wallet/challenge', json={'address': wallet.address}).json()
        signature = Account.sign_message(encode_defunct(text=challenge['message']), wallet.key).signature.hex()
        result = self.owner.post('/api/wallet/verify', json={'challenge_id': challenge['challenge_id'], 'signature': signature})
        self.assertEqual(result.json()['user']['id'], self.owner_user['id'])

    def test_wrong_wallet_signature_rejected(self):
        wallet, wrong = Account.create(), Account.create()
        challenge = self.owner.post('/api/wallet/challenge', json={'address': wallet.address}).json()
        signature = Account.sign_message(encode_defunct(text=challenge['message']), wrong.key).signature.hex()
        self.assertEqual(self.owner.post('/api/wallet/verify', json={'challenge_id': challenge['challenge_id'], 'signature': signature}).status_code, 401)

    def test_websocket_notification_and_origin(self):
        with self.owner.websocket_connect('/ws/projects/'+self.pid, headers={'origin': 'http://testserver'}) as socket:
            self.assertEqual(socket.receive_json()['type'], 'ready')
            result = self.owner.post(f'/api/projects/{self.pid}/messages', json={'content': 'notify live'})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(socket.receive_json()['type'], 'changed')
            socket.send_text('ping')
            self.assertEqual(socket.receive_json()['type'], 'pong')
        from starlette.websockets import WebSocketDisconnect
        with self.assertRaises(WebSocketDisconnect):
            with self.owner.websocket_connect('/ws/projects/'+self.pid, headers={'origin': 'http://evil.example'}):
                pass

    def test_ai_missing_credentials_does_not_fake_output(self):
        with patch.dict(os.environ, {'RELAY_AI_API_KEY': ''}):
            before = len(self.project()['messages'])
            response = self.owner.post(f'/api/projects/{self.pid}/agents/run', json={'kind': 'writer', 'instruction': 'write a draft'})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(len(self.project()['messages']), before)


if __name__ == '__main__':
    unittest.main()
