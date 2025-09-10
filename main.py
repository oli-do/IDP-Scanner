import asyncio
import json
import os
import platform
import subprocess
from multiprocessing import Manager
from tkinter import Tk, filedialog

from nicegui import ui, app, run, events

from core import init
from utils import PapyrusFilter, get_xml_files

proceed_event = asyncio.Event()
skip_scan = False
issue_num = 0
stop_while = False
target_files = []
issue_filter = []
issue_filter_indices = []
issue_indices_counter = -1


async def wait_for_button():
    await proceed_event.wait()


@ui.page('/scan')
async def scan():
    global issue_num
    global stop_while
    global skip_scan
    global target_files
    global issue_filter
    global issue_filter_indices
    stop_while = False
    if not skip_scan:
        progress_q = Manager().Queue()
        file_q = Manager().Queue()
        with ui.card().classes('fixed-center items-center  w-[90vw]') as card:
            ui.label('Please wait while XML files are being scanned for potential issues...')
            ui.spinner()

            def progress_bar(command: str = ''):
                timer = ui.timer(0.0001,
                                 callback=lambda: progressbar.set_value(
                                     progress_q.get_nowait() if not progress_q.empty() else progressbar.value))
                progressbar = ui.linear_progress(value=0, show_value=False).props('instant-feedback')
                if command == 'stop':
                    timer.active = False
                    progressbar.delete()

            def log(command: str = ''):
                timer = ui.timer(0.0001,
                                 callback=lambda: logger.push(
                                     file_q.get() if not file_q.empty() else '', classes='text-grey')).props(
                    'instant-feedback')
                logger = ui.log(max_lines=os.cpu_count()).classes('h-20 items-center')
                if command == 'stop':
                    timer.active = False
                    logger.delete()

            progress_bar()
            log()
        results = await run.cpu_bound(init, target_files, progress_q, file_q)
        progress_bar('stop')
        log('stop')
        card.delete()
        issue_num = 0
    else:
        results = app.storage.general['session']['data']
        try:
            issue_num = app.storage.general['session']['i']
        except KeyError:
            issue_num = 0
        try:
            issue_filter = app.storage.general['session']['filter']
            issue_filter_indices = app.storage.general['session']['filter_indices']
        except KeyError:
            with ui.dialog() as dialog, ui.card().classes('items-center  w-[90vw]'):
                ui.label(
                    'ERROR: The session you tried to load is incompatible with this version of IDP-Scanner. Please start a new session.').tailwind.text_color(
                    'red-500').text_align('center')
                ui.button('OK', on_click=lambda: ui.navigate.to('/'))
            dialog.open()
            await dialog
    with ui.row().classes('w-full justify-start'):
        ui.chip('Back to Main Menu', on_click=lambda: change_scan(), icon='navigate_before').props('outline square')
    expand_issues = True
    expand_fab = False
    keyboard = ui.keyboard(on_key=handle_key)
    app.storage.general['session'] = {'i': issue_num, 'filter': issue_filter, 'filter_indices': issue_filter_indices,
                                      'data': results}
    while issue_num < len(results):
        r = results[issue_num]
        with ui.card().classes('fixed-center items-center w-[90vw]').props('instant-feedback') as card:
            xml = r['xml']
            line = r['line']
            forbidden = r['forbidden']
            with ui.expansion('Potential Issues', icon='announcement', value=expand_issues).classes(
                    'bg-orange-4 w-full').props('square') as expansion:
                with ui.row():
                    for f in forbidden:
                        ui.chip(text=f).classes('bg-orange-2')

            ui.separator()
            file_path = str(os.path.join(app.storage.general['idp_data_path'], r['file_path']))
            with ui.column().classes('w-full'):
                if 'editor_theme' in app.storage.general:
                    theme = app.storage.general['editor_theme']
                else:
                    theme = 'aura'
                code_m = ui.codemirror(xml, language='XML', line_wrapping=True, theme=theme).classes('w-full').style(
                    'cursor: text;')
                code_m.on('keydown.ctrl.s', lambda: on_save(file_path, line, code_m.value))
                code_m.on('keydown.ctrl.o', lambda: open_file(file_path))
            ui.label(file_path).tailwind.font_weight('light')
            with ui.row().classes('items-center justify-center'):
                with ui.fab('settings', color='white', value=expand_fab, direction='up').classes('square') as fab:
                    with ui.card():
                        ui.select(code_m.supported_themes, label='Editor Theme',
                                  on_change=lambda: editor_theme_changed(code_m.theme, fab)).classes('w-32').bind_value(
                            code_m, 'theme')
                with ui.button_group():
                    with ui.button('←', on_click=lambda: previous_issue()) as prev_button:
                        ui.tooltip('Previous issue (Page Up)')
                    if issue_num <= 0:
                        prev_button.disable()
                    with ui.button(on_click=lambda: open_file(file_path), icon='file_open'):
                        ui.tooltip('Open file (CTRL+O in XML Editor)')
                    with ui.button(icon='filter_alt',
                                   on_click=lambda e: filter_issues(filter_button, results)) as filter_button:
                        ui.tooltip('Filter issues')
                    if issue_filter_indices or issue_filter:
                        filter_button.props('text-color=green-400')
                    with ui.button(on_click=lambda: on_save(file_path, line, code_m.value), icon='save'):
                        ui.tooltip('Save changes (CTRL+S in XML Editor)')
                    with ui.button('→', on_click=next_issue):
                        ui.tooltip('Next issue (Page Down)')
                with ui.row().classes('items-center m-auto'):
                    num_input = ui.number(value=issue_num + 1, min=1, max=len(results),
                                          label=' / ' + str(len(results))).props(
                        f'size={len(str(len(results)))}')
                    num_input.on('keydown.enter', lambda: jump_to_issue(int(num_input.value) - 1))
                    with ui.circular_progress(value=issue_num / len(results), show_value=False, color='green-700'):
                        ui.icon(name='task_alt', size='lg', color='green-500')
            await wait_for_button()
            save_session()
            expand_issues = expansion.value
            expand_fab = fab.value
            proceed_event.clear()
            if stop_while:
                break
            card.delete()
    keyboard.active = False
    if stop_while:
        ui.navigate.to('/')
        return
    with ui.card().classes('fixed-center items-center') as final_card:
        with ui.row().classes('items-center m-auto'):
            with ui.circular_progress(value=1.0, show_value=False, color='green-700'):
                ui.icon(name='task_alt', size='lg', color='green-500')
        ui.label('Completed.').tailwind.text_color('green-700')
        with ui.row():
            scan_button = ui.button('Scan again', on_click=lambda: scan_again(scan_button, final_card), icon='restore')


def save_session():
    app.storage.general['session']['i'] = issue_num
    app.storage.general['session']['filter'] = issue_filter
    app.storage.general['session']['filter_indices'] = issue_filter_indices


async def filter_issues(filter_button: ui.button, issues: list):
    global issue_filter
    forbidden = []
    for issue_dict in issues:
        list_forbidden = issue_dict['forbidden']
        for f in list_forbidden:
            forbidden.append(f)
    forbidden_unique = list(set(forbidden))
    forbidden_counted = {}
    for f in forbidden_unique:
        forbidden_counted[f] = forbidden.count(f)
    forbidden_unique = dict(sorted(forbidden_counted.items(), key=lambda item: item[1], reverse=True))
    with ui.dialog() as dialog, ui.card().classes('w-full'):
        with ui.row().classes('w-full justify-end'):
            ui.button(icon='close', on_click=dialog.close)
        with ui.row().classes('w-full justify-center'):
            ui.chip('Click on an issue to add it to the active filter. Click again to remove it.',
                    icon='info').tailwind.background_color('white')
        with ui.scroll_area().classes('w-full'):
            with ui.grid(columns=2).classes('w-max m-auto items-center gap-4').style(
                    'grid-template-columns: auto auto;'):
                ui.label('Potential Issue').tailwind.font_weight('bold')
                ui.label('Overall Count').tailwind.font_weight('bold')
                for key, value in forbidden_unique.items():
                    c = ui.chip(text=key, selectable=True,
                                on_click=lambda e: filter_changed(e, issues, dialog, filter_button)).classes(
                        'bg-orange-2')
                    if key in issue_filter:
                        c.selected = True
                    with ui.row().classes('items-center m-auto'):
                        ui.label(text=str(value))
    dialog.open()


async def filter_changed(e: events.ClickEventArguments, issues: list, dialog: ui.dialog | None,
                         filter_button: ui.button):
    global issue_filter
    global issue_filter_indices
    issue_filter_indices = []
    chip = e.sender
    text = ''
    if isinstance(chip, ui.chip):
        text = chip.text
    if text:
        if text in issue_filter:
            issue_filter.remove(text)
        else:
            issue_filter.append(text)
    for i in range(len(issues)):
        forbidden = issues[i]['forbidden']
        for filter_word in issue_filter:
            if filter_word in forbidden:
                issue_filter_indices.append(i)
    if issue_filter_indices:
        issue_filter_indices = sorted(set(issue_filter_indices))
        filter_button.props('text-color=green-400')
        if dialog:
            await dialog.on('hide', next_issue)
    else:
        filter_button.props(remove='text-color')
        save_session()
        if dialog:
            await dialog.on('hide', None)


async def handle_key(e: events.KeyEventArguments):
    if e.key.page_down and not e.action.repeat:
        if e.action.keydown:
            await next_issue()
    if e.key.page_up and not e.action.repeat:
        if e.action.keydown:
            await previous_issue()


def jump_to_issue(value: int):
    global issue_num
    if value < 0:
        value = 0
    issue_num = value
    proceed_event.set()


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
    global issue_filter_indices
    global issue_indices_counter
    if issue_filter_indices:
        issue_indices_counter += 1
        for i in range(len(issue_filter_indices)):
            if issue_filter_indices[i] > issue_num:
                issue_indices_counter = i
                jump_to_issue(issue_filter_indices[issue_indices_counter])
                ui.notify(f'Jumped to filter match ({issue_indices_counter + 1}/{len(issue_filter_indices)})',
                          type='info', timeout=400)
                return
        jump_to_issue(issue_filter_indices[0])
        ui.notify(f'Jumped to filter match (1/{len(issue_filter_indices)})', type='info', timeout=400)
    else:
        issue_num += 1
        proceed_event.set()


async def previous_issue():
    global issue_num
    global issue_filter_indices
    global issue_indices_counter
    if issue_filter_indices:
        issue_indices_counter -= 1
        target_indices = []
        for i in range(len(issue_filter_indices)):
            if issue_filter_indices[i] < issue_num:
                issue_indices_counter = i
                target_indices.append(issue_filter_indices[i])
        if target_indices:
            jump_to_issue(issue_filter_indices[issue_indices_counter])
            ui.notify(f'Jumped to filter match ({issue_indices_counter + 1}/{len(issue_filter_indices)})', type='info',
                      timeout=400)
            return
        else:
            jump_to_issue(issue_filter_indices[-1])
            ui.notify(f'Jumped to filter match ({len(issue_filter_indices)}/{len(issue_filter_indices)})', type='info',
                      timeout=400)
    else:
        if issue_num > 0:
            issue_num -= 1
            proceed_event.set()


async def change_scan():
    global stop_while
    global skip_scan
    global issue_filter
    global issue_filter_indices
    issue_filter = []
    issue_filter_indices = []
    skip_scan = False
    stop_while = True
    proceed_event.set()
    app.storage.general.pop('target')


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
async def index():
    global target_files
    target_files = []
    if 'session' in app.storage.general:
        with ui.dialog().props('persistent') as dialog, ui.card().classes('fixed-center items-center') as dialog_field:
            ui.label('Continue working on last session?')
            with ui.row():
                yes_button = ui.button('Yes', on_click=lambda: continue_working([yes_button, no_button], dialog_field))
                no_button = ui.button('No', on_click=lambda: new_settings(dialog))
        dialog.open()
    with ui.card().classes('fixed-center items-center').style('max-height: 95%; overflow-y: auto;'):
        holder = {}
        with ui.button('IDP.DATA DIRECTORY', icon='ads_click',
                       on_click=lambda: pick_folder(target_selector.value, holder, expansion_expert_settings,
                                                    card_expert_settings)):
            ui.tooltip('Locate your local idp.data repository')
        dir_label()
        ui.separator()
        with ui.expansion('Session Management', icon='manage_accounts'):
            with ui.card().classes('items-center m-auto border bg-gray-200'):
                ui.button('Export Session', icon='vertical_align_top', color='gray-100',
                          on_click=export_session).classes('w-full')
                ui.button('Import Session', icon='vertical_align_bottom', color='gray-100',
                          on_click=import_session).classes('w-full')
        ui.separator().props('size=3px')
        with ui.row().classes('items-center m-auto'):
            target_selector = ui.select(['Complete Scan', 'DCLP', 'DDbDP'], value='Complete Scan',
                                        label='Target',
                                        on_change=lambda e: target_changed(card_expert_settings, e.value, holder,
                                                                           expansion_expert_settings)).classes(
                'w-[200px]')
        with ui.expansion(icon='settings', text='Expert Settings').classes('items-center') as expansion_expert_settings:
            with ui.card().classes('items-center m-auto border bg-blue-50') as card_expert_settings:
                draw_expert_settings(target_selector.value, holder, expansion_expert_settings)
        if not 'idp_data_path' in app.storage.general:
            expansion_expert_settings.disable()
        ui.separator().props('size=3px')
        lang_selector = ui.select(['Exclude Latin', 'Greek Only'], value='Exclude Latin',
                                  label='xml:lang Preset').classes('w-[200px]')
        holder['scan_button'] = ui.button('SCAN', icon='troubleshoot',
                                          on_click=lambda: start(holder['scan_button'], target_selector.value,
                                                                 lang_selector.value))


async def export_session():
    if not 'session' in app.storage.general:
        ui.notify('No active session to export', type='negative')
    else:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, save_file_dialog)
        if file_path:
            try:
                json.dump(app.storage.general['session'], open(file_path, 'w', encoding='utf-8'), ensure_ascii=False,
                          indent=4)
                ui.notify('Successfully exported session', type='positive')
            except IOError:
                ui.notify('Failed to export session', type='negative')


async def import_session():
    if not 'idp_data_path' in app.storage.general:
        ui.notify('IDP.DATA Directory must be set to import a session', type='negative')
        return
    loop = asyncio.get_running_loop()
    file_path = await loop.run_in_executor(None, open_file_dialog)
    if file_path:
        try:
            session = json.load(open(file_path, 'r', encoding='utf-8'))
            app.storage.general['session'] = session
        except (IOError, json.JSONDecodeError) as e:
            ui.notify(f'Failed to import session: {e}', type='negative')
            return
        required_keys = ['i', 'filter', 'filter_indices', 'data']
        if all(key in session for key in required_keys):
            ui.notify('Successfully imported session', type='positive')
            with ui.dialog().props('persistent') as dialog, ui.card().classes('items-center') as card:
                with ui.row().classes('items-center'):
                    ui.label('Loading Session...')
            dialog.open()
            await continue_working([], card)
        else:
            ui.notify('Failed to import session: Invalid or damaged data.', type='negative')


def save_file_dialog():
    root = Tk()
    root.attributes('-topmost', 'True')
    root.withdraw()
    return filedialog.asksaveasfilename(initialdir=os.getcwd(), initialfile='idp-scanner-session.json',
                                        confirmoverwrite=True, filetypes=[('JSON File', '*.json')],
                                        defaultextension='.json')


def open_file_dialog():
    root = Tk()
    root.attributes('-topmost', 'True')
    root.withdraw()
    return filedialog.askopenfilename(filetypes=[('JSON File', '*.json')], defaultextension='.json')


def draw_expert_settings(target: str, holder, expansion_expert_settings: ui.expansion):
    global target_files
    try:
        idp_data_path = app.storage.general['idp_data_path']
    except KeyError:
        expansion_expert_settings.disable()
        return
    dclp_files, ddb_files, all_files = get_xml_files(idp_data_path)
    if target == 'Complete Scan':
        target_files = all_files
    elif target == 'DCLP':
        target_files = dclp_files
    else:
        target_files = ddb_files
    with ui.expansion(text='Filter').classes('w-full'):
        ui.label('Only include papyri which match the specified criteria.').tailwind.font_weight('light')
        input_ddb_collection_name = ui.input(label='DDbDP Collection Name').classes('w-full')
        if target == 'DDbDP':
            input_ddb_collection_name.set_visibility(True)
        else:
            input_ddb_collection_name.set_visibility(False)
        input_dclp_hybrid = ui.input(label='TEI:idno[@type="dclp-hybrid"]').classes('w-full')
        if target == 'DCLP':
            input_dclp_hybrid.set_visibility(True)
        else:
            input_dclp_hybrid.set_visibility(False)
        input_title = ui.input(label='TEI:title').classes('w-full')
        input_orig_place = ui.input(label='TEI:origPlace').classes('w-full')
        with ui.grid().classes('m-auto'):
            with ui.switch('Single match suffices', value=True) as cb_single_match:
                ui.tooltip('Toggle: One criterion must match / All criteria must match')
            button_apply_filter = ui.button('Apply Filter', on_click=lambda e: apply_filter(button_apply_filter, holder,
                                                                                            expansion_expert_settings,
                                                                                            input_ddb_collection_name.value,
                                                                                            input_dclp_hybrid.value,
                                                                                            input_title.value,
                                                                                            input_orig_place.value,
                                                                                            cb_single_match.value,
                                                                                            target_files,
                                                                                            input_min,
                                                                                            input_max,
                                                                                            pr
                                                                                            ))
    ui.separator()
    with ui.expansion('Processing Range').classes('items-center w-full'):
        ui.label(
            'Pythonic range which determines which files between index "Start" and index "End" should be '
            'processed.').tailwind.font_weight('light')
        with ui.row().classes('items-center w-full'):
            max_len = len(target_files)
            input_min = ui.number(label='Start', min=0, on_change=lambda: pr.set_value(
                {'min': int(input_min.value), 'max': pr.value['max']}), value=0).classes('w-[15vw]')
            input_max = ui.number(label='End', min=0, max=max_len, on_change=lambda: pr.set_value(
                {'min': pr.value['min'], 'max': input_max.value}), value=max_len).classes('w-[15vw]')
        pr = ui.range(min=0, max=max_len, value={'min': input_min.value, 'max': input_max.value},
                      on_change=lambda e: range_changed(e, input_min, input_max))
        with ui.row().classes('items-center m-auto'):
            ui.button('Apply Processing Range',
                      on_click=lambda: apply_range(int(input_min.value), int(input_max.value),
                                                   expansion_expert_settings))


async def target_changed(card_expert_settings: ui.card, target: str, holder, expansion_expert_settings: ui.expansion):
    card_expert_settings.clear()
    with card_expert_settings:
        draw_expert_settings(target, holder, expansion_expert_settings)


async def range_changed(e, input_min: ui.number, input_max: ui.number):
    input_min.set_value(e.value['min'])
    input_max.set_value(e.value['max'])


async def apply_range(start_val: int, end_val: int, expansion_expert_settings: ui.expansion):
    global target_files
    target_files = target_files[start_val:end_val]
    ui.notify(f'Range applied. Processing limited to {len(target_files)} files.', type='info', close_button=True)
    expansion_expert_settings.close()


async def apply_filter(sender: ui.button, holder, expansion_expert_settings: ui.expansion,
                       ddb_collection_name: str, dclp_hybrid: str, title: str, orig_place: str,
                       single_match: bool, file_target: list[str], input_min: ui.number, input_max: ui.number,
                       pr: ui.range):
    global target_files
    sender.disable()
    scan_button = holder['scan_button']
    scan_button.disable()
    with ui.row().classes('m-auto'):
        spinner = ui.spinner()
    pap_filter = PapyrusFilter(file_target, ddb_collection_name, dclp_hybrid, title, orig_place, single_match)
    target_files = await run.cpu_bound(pap_filter.filter)
    spinner.delete()
    sender.enable()
    scan_button.enable()
    expansion_expert_settings.close()
    len_target_files = len(target_files)
    input_min.max = len(target_files)
    input_max.max = len(target_files)
    input_min.value = 0
    input_max.value = len_target_files
    pr.max = len_target_files
    pr.set_value({'min': input_min.value, 'max': input_max.value})
    ui.notify(f'Filtered {len_target_files} files.', type='info', close_button=True)


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
    global target_files
    app.storage.general['target'] = target
    app.storage.general['preset'] = preset
    if not 'idp_data_path' in app.storage.general:
        ui.notify('IDP.Data directory must be set', type='negative')
        return
    idp_data_path = app.storage.general['idp_data_path']
    dclp_files, ddb_files, all_files = get_xml_files(idp_data_path)
    if not target_files:
        if target == 'DCLP':
            target_files = dclp_files
        elif target == 'DDbDP':
            target_files = ddb_files
        else:
            target_files = all_files
    sender.disable()
    ui.spinner()
    ui.navigate.to('/scan')


def open_dialog() -> str:
    root = Tk()
    root.attributes('-topmost', 'True')
    root.withdraw()
    return filedialog.askdirectory()


async def pick_folder(target: str, holder, expansion_expert_settings: ui.expansion, card_expert_settings: ui.card):
    loop = asyncio.get_running_loop()
    folder = await loop.run_in_executor(None, open_dialog)
    if folder:
        if os.path.exists(os.path.join(folder, 'DCLP')) and os.path.exists(os.path.join(folder, 'DDB_EpiDoc_XML')):
            app.storage.general['idp_data_path'] = os.path.normpath(folder)
            dir_label.refresh()
            expansion_expert_settings.enable()
            with card_expert_settings:
                draw_expert_settings(target, holder, expansion_expert_settings)
            ui.notify('Successfully set IDP.Data directory', type='positive')
        else:
            ui.notify('Invalid directory', type='warning')


ui.run(native=True, window_size=(900, 800), fullscreen=False, title='IDP Scanner', reload=False)
