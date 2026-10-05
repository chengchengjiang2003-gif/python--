"""可选浏览器验收；需要 playwright。请指向单独的测试实例。"""
import argparse
import secrets
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8000')
parser.add_argument('--chromium')
parser.add_argument('--output', default='/tmp/relay-browser')
args = parser.parse_args()
base = args.url.rstrip('/')
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
suffix = secrets.token_hex(4)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, **({'executable_path': args.chromium} if args.chromium else {}))
    a = browser.new_context(viewport={'width':1440, 'height':1000})
    b = browser.new_context(viewport={'width':1280, 'height':900})
    owner, member = a.new_page(), b.new_page()
    errors = []
    for page in (owner, member):
        page.on('pageerror', lambda e: errors.append(str(e)))

    def register(page, username, name):
        page.goto(base)
        page.locator('#register-tab').click()
        page.locator('#auth-username').fill(username)
        page.locator('#auth-name').fill(name)
        page.locator('#auth-password').fill('browser-test-pass')
        page.locator('#auth-submit').click()
        expect(page.locator('#application')).to_be_visible()
        expect(page.locator('#task-count')).to_have_text('3')
        expect(page.locator('#connection')).to_have_text('实时连接')

    try:
        register(owner, 'e2e_owner_'+suffix, '小林')
        register(member, 'e2e_member_'+suffix, '阿远')
        owner.locator('#invite-open').click()
        owner.locator('#invite-form button').click()
        expect(owner.locator('#invite-token')).to_be_visible()
        token = owner.locator('#invite-token').input_value()
        owner.keyboard.press('Escape')
        member.locator('#project-switch').click()
        member.locator('#join-project').click()
        member.locator('#join-form input').fill(token)
        member.locator('#join-form button').click()
        expect(member.locator('#current-role')).to_have_text('阿远 · 协作者')
        expect(owner.locator('#member-count')).to_have_text('房间成员 · 2')
        print('PASS: two independent users register, invite and join', flush=True)

        owner.locator('#message-input').fill('<b>同步消息</b>：一起推进')
        owner.locator('#message-form button').click()
        expect(member.locator('.message-text').filter(has_text='<b>同步消息</b>：一起推进')).to_be_visible()
        assert member.locator('.message-text b').count() == 0
        print('PASS: realtime discussion synchronized as safe text', flush=True)

        owner.locator('#tab-docs').click()
        member.locator('#tab-docs').click()
        owner.locator('#document').fill('第一版共同文档：明确项目任务、权限和交付标准。')
        owner.locator('#save-doc').click()
        expect(member.locator('#document')).to_have_value('第一版共同文档：明确项目任务、权限和交付标准。')
        member.locator('#document').fill('成员正在编辑的草稿，不能被静默覆盖。')
        owner.locator('#document').fill('发起人新版本：加入验收规则。')
        owner.locator('#save-doc').click()
        expect(member.locator('#doc-status')).to_contain_text('其他成员已更新')
        assert member.locator('#document').input_value() == '成员正在编辑的草稿，不能被静默覆盖。'
        member.locator('#save-doc').click()
        expect(member.locator('#merge-form')).to_be_visible()
        member.locator('#merge-form textarea').fill('合并后的共同版本：加入验收规则并保留成员建议。')
        member.locator('#merge-form button[type=submit]').click()
        expect(owner.locator('#document')).to_have_value('合并后的共同版本：加入验收规则并保留成员建议。')
        print('PASS: shared document and conflict merge', flush=True)

        owner.locator('#file-input').set_input_files({'name':'team-notes.txt', 'mimeType':'text/plain', 'buffer':b'private collaborative file'})
        expect(member.locator('#files-list a')).to_have_text('team-notes.txt')
        url = member.locator('#files-list a').get_attribute('href')
        response = b.request.get(base+url)
        assert response.status == 200 and response.body() == b'private collaborative file'
        print('PASS: upload persisted and authorized download', flush=True)

        owner.locator('#tab-tasks').click()
        member.locator('#tab-tasks').click()
        target_a = owner.get_by_role('button').filter(has=owner.get_by_role('heading', name='实现产品发布页', exact=True))
        target_a.click()
        owner.locator('#task-assignee').select_option(label='阿远')
        owner.locator('#reassign-task').click()
        expect(owner.locator('#task-assignee')).to_have_value(b.request.get(base+'/api/me').json()['user']['id'])
        owner.keyboard.press('Escape')
        target_b = member.get_by_role('button').filter(has=member.get_by_role('heading', name='实现产品发布页', exact=True))
        expect(target_b).to_contain_text('阿远')
        target_b.click()
        member.locator('#start-task').click()
        member.locator('#submit-open').click()
        member.locator('#submission-form textarea').fill('发布页已实现，支持桌面和移动端，核心交互已完成检查。')
        member.locator('#submission-form button').click()
        expect(member.locator('#modal-backdrop')).to_be_hidden()
        expect(target_a).to_contain_text('已保存交付版本')
        target_a.click()
        owner.locator('#approve-task').click()
        expect(owner.locator('#paid-budget')).to_contain_text('40')
        expect(member.locator('#paid-budget')).to_contain_text('40')
        print('PASS: assignment, submission, approval and both-client updates', flush=True)

        owner.locator('#tab-settlements').click()
        expect(owner.locator('#settlement-list')).to_contain_text('阿远')
        owner.locator('#tab-tasks').click()
        owner.locator('#toast').evaluate('(element) => { element.hidden = true; }')
        owner.screenshot(path=str(out/'desktop.png'), full_page=True)
        owner.set_viewport_size({'width':390, 'height':844})
        assert owner.evaluate('document.documentElement.scrollWidth <= innerWidth')
        owner.screenshot(path=str(out/'mobile.png'), full_page=True)
        owner.locator('#mobile-members').click()
        expect(owner.locator('#modal-title')).to_have_text('成员与项目权限')
        owner.keyboard.press('Escape')
        print('PASS: desktop and mobile layout and member controls', flush=True)

        owner.locator('#account-open').click()
        owner.locator('#logout').click()
        expect(owner.locator('#auth-screen')).to_be_visible()
        owner.locator('#auth-username').fill('e2e_owner_'+suffix)
        owner.locator('#auth-password').fill('browser-test-pass')
        owner.locator('#auth-submit').click()
        expect(owner.locator('#paid-budget')).to_contain_text('40')
        assert not errors, errors
        print('PASS: login retains ledger; no browser JavaScript errors', flush=True)
    except BaseException:
        owner.screenshot(path=str(out/'failure-owner.png'), full_page=True)
        member.screenshot(path=str(out/'failure-member.png'), full_page=True)
        raise
    finally:
        browser.close()
