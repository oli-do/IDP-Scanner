from nicegui import ui, app, run
from tkinter import Tk, filedialog
from core import init
import asyncio
from configparser import ConfigParser
import os
import subprocess
import platform
from multiprocessing import Manager

proceed_event = asyncio.Event()
skip_scan = False
issue_num = 0
stop_while = False

async def wait_for_button():
    await proceed_event.wait()

@ui.page('/scan')
async def scan():
    global issue_num
    global stop_while
    global skip_scan
    stop_while = False
    if not skip_scan:
        progress_q = Manager().Queue()
        file_q = Manager().Queue()
        with ui.card().classes('fixed-center items-center  w-[90vw]') as card:
            ui.label('Please wait while XML files are being scanned for potential issues...')
            ui.spinner()
            def progress_bar(command: str = ''):
                timer = ui.timer(0.0001,
                         callback=lambda: progressbar.set_value(progress_q.get_nowait() if not progress_q.empty() else progressbar.value))
                progressbar = ui.linear_progress(value=0, show_value=False).props('instant-feedback')
                if command == 'stop':
                    timer.active = False
                    progressbar.delete()
            def log(command: str = ''):
                timer = ui.timer(0.0001,
                                 callback=lambda: logger.push(
                                     file_q.get() if not file_q.empty() else '', classes='text-grey')).props('instant-feedback')
                logger = ui.log(max_lines=os.cpu_count()).classes('h-20 items-center')
                if command == 'stop':
                    timer.active = False
                    logger.delete()
            progress_bar()
            log()
        results = await run.cpu_bound(init, progress_q, file_q)
        progress_bar('stop')
        log('stop')
        card.delete()
        issue_num = 0
    else:
        results = app.storage.general['session']['data']
        issue_num = app.storage.general['session']['i']
    app.storage.general['session'] = {'i': issue_num, 'data': results}
    with ui.row().classes('w-full justify-start'):
        ui.chip('Back to Main Menu', on_click=lambda: change_scan(), icon='navigate_before').props('outline square')
    expand_issues = True
    expand_fab = False
    while issue_num < len(results):
        r = results[issue_num]
        with ui.card().classes('fixed-center items-center w-[90vw]').props('instant-feedback') as card:
            xml = r['xml']
            line = r['line']
            forbidden = r['forbidden']
            with ui.expansion('Potential Issues', icon='announcement', value=expand_issues).classes('bg-orange-4 w-full').props('square') as expansion:
                with ui.row():
                    for f in forbidden:
                        ui.chip(text=f, selectable=True).classes('bg-orange-2')
            ui.separator()
            file_path = r['file_path']
            with ui.column().classes('w-full'):
                if 'editor_theme' in app.storage.general:
                    theme = app.storage.general['editor_theme']
                else:
                    theme = 'aura'
                code_m = ui.codemirror(xml, language='XML', line_wrapping=True, theme=theme).classes('w-full').style('cursor: text;')
            ui.label(file_path).tailwind.font_weight('light')
            with ui.row().classes('items-center justify-center'):
                with ui.fab('settings', color='white', value=expand_fab, direction='up').classes('square') as fab:
                    with ui.card():
                        ui.select(code_m.supported_themes, label='Editor Theme', on_change=lambda: editor_theme_changed(code_m.theme, fab)).classes('w-32').bind_value(code_m, 'theme')
                prev_button = ui.button('← Previous', on_click=lambda: previous_issue())
                if issue_num == 0:
                    prev_button.disable()
                ui.button('Open File', on_click=lambda: open_file(file_path), icon='file_open')
                ui.button('Save Changes', on_click=lambda: on_save(file_path, line, code_m.value), icon='save')
                ui.button('Next →', on_click=next_issue)
                with ui.row().classes('items-center m-auto'):
                    with ui.circular_progress(value=issue_num / len(results), show_value=False, color='green-700'):
                        ui.icon(name='task_alt', size='lg', color='green-500')
            await wait_for_button()
            app.storage.general['session']['i'] = issue_num
            expand_issues = expansion.value
            expand_fab = fab.value
            proceed_event.clear()
            if stop_while:
                break
            card.delete()
    if stop_while:
        return
    with ui.card().classes('fixed-center items-center') as final_card:
        with ui.row().classes('items-center m-auto'):
            with ui.circular_progress(value=1.0, show_value=False, color='green-700'):
                ui.icon(name='task_alt', size='lg', color='green-500')
        ui.label('Completed.').tailwind.text_color('green-700')
        app.storage.general.pop('session')
        with ui.row():
            scan_button = ui.button('Scan again', on_click=lambda: scan_again(scan_button, final_card), icon='restore')

async def editor_theme_changed(theme, fab: ui.fab):
    app.storage.general['editor_theme'] = theme
    fab.close()

async def scan_again(sender: ui.button, card: ui.card):
    global skip_scan
    sender.disable()
    skip_scan = False
    with card:
        ui.spinner()
    ui.navigate.to('/scan')


async def next_issue():
    global issue_num
    issue_num += 1
    proceed_event.set()


async def previous_issue():
    global issue_num
    if issue_num > 0:
        issue_num -= 1
        proceed_event.set()


async def change_scan():
    global stop_while
    global skip_scan
    skip_scan = False
    stop_while = True
    proceed_event.set()
    app.storage.general.pop('target')
    ui.navigate.to('/')


async def open_file(filepath: str):
    if platform.system() == 'Darwin':
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':
        os.startfile(filepath)
    else:
        subprocess.call(('xdg-open', filepath))


async def on_save(file_path: str, line: int, new_text: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    lines = file_content.splitlines()
    lines[line] = new_text
    new_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content + '\n')
    ui.notify('Successfully wrote changes', type='positive')

@ui.page('/')
def index():
    if 'session' in app.storage.general:
        with ui.dialog() as dialog, ui.card().classes('fixed-center items-center') as dialog_field:
            ui.label('Continue working on last session?')
            with ui.row():
                yes_button = ui.button('Yes', on_click=lambda: continue_working([yes_button, no_button], dialog_field))
                no_button = ui.button('No', on_click=lambda: new_settings(dialog))
        dialog.open()
    with ui.card().classes('fixed-center items-center'):
        with ui.button('IDP.DATA DIRECTORY', icon='ads_click', on_click=lambda: pick_folder(), color='grey'):
            ui.tooltip('Locate your local idp.data repository')
        dir_label()
        ui.separator()
        target_selector = ui.select(['Complete Scan', 'DCLP', 'DDbDP'], value='Complete Scan', label='Target').classes('w-[200px]')
        lang_selector = ui.select(['Exclude Latin', 'Greek Only'], value='Exclude Latin', label='xml:lang Preset').classes('w-[200px]')
        scan_button = ui.button('SCAN', icon='troubleshoot', on_click=lambda: start(scan_button, target_selector.value, lang_selector.value))


@ui.refreshable
def dir_label():
    try:
        ui.label(app.storage.general['idp_data_path']).tailwind.font_weight('light').text_align('center')
    except KeyError:
        pass

async def new_settings(dialog: ui.dialog):
    global skip_scan
    skip_scan = False
    dialog.close()

async def continue_working(buttons: list[ui.button], dialog_field: ui.card):
    for button in buttons:
        button.disable()
    global skip_scan
    with dialog_field:
        ui.spinner()
    skip_scan = True
    ui.navigate.to('/scan')


async def start(sender: ui.button, target: str, preset: str):
    app.storage.general['target'] = target
    app.storage.general['preset'] = preset
    if not 'idp_data_path' in app.storage.general:
        ui.notify('IDP.Data directory must be set', type='negative')
        return
    sender.disable()
    ui.spinner()
    ui.navigate.to('/scan')


def open_dialog() -> str:
    root = Tk()
    root.attributes('-topmost', 'True')
    root.withdraw()
    return filedialog.askdirectory()


async def pick_folder():
    loop = asyncio.get_running_loop()
    folder = await loop.run_in_executor(None, open_dialog)
    if folder:
        if os.path.exists(os.path.join(folder, 'DCLP')) and os.path.exists(os.path.join(folder, 'DDB_EpiDoc_XML')):
            app.storage.general['idp_data_path'] = folder
            dir_label.refresh()
            ui.notify('Successfully set IDP.Data directory', type='positive')
        else:
            ui.notify('Invalid directory', type='warning')


config = ConfigParser()
config.read('settings.ini')
window_size = (config.getint('WINDOW', 'width'), config.getint('WINDOW', 'height'))
ui.run(native=True, window_size=window_size, fullscreen=False, title='IDP Data Scanner')
