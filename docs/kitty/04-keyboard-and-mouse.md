# Keyboard shortcuts and mouse bindings in kitty

This guide explains how keyboard shortcuts and mouse bindings work in kitty 0.48.2 as bundled in Kilix on Linux. It covers the `map` line and how to write key names, how to remove or replace default shortcuts, multi-key sequences, keyboard modes, conditional shortcuts, running several actions from one key, action aliases, sending keys and text to programs, the `mouse_map` line, tools for debugging shortcuts, and complete tables of the default Linux keyboard shortcuts and mouse bindings.

## Add a keyboard shortcut

A keyboard shortcut is one `map` line in `kitty.conf`:

```
map [OPTIONS] KEYS ACTION [ARGUMENTS...]
```

For example, to open a new tab with `F7`:

```
map f7 new_tab
```

A key is written as modifiers joined to a key name with `+`, such as `ctrl+alt+d`. Letters and other printable keys are written as the lowercase character (`d`, `[`, `/`). The modifiers are `ctrl` (or `control`), `shift`, `alt` (or `opt`, `option`) and `super` (or `cmd`, `command`).

After saving `kitty.conf`, kitty reloads it automatically, so the new shortcut works straight away.

## Name special keys in a shortcut

Keys that do not type a character have names. Names used by kitty's defaults include `enter`, `escape` (also `esc`), `tab`, `backspace`, `delete`, `insert`, `home`, `end`, `page_up`, `page_down`, `up`, `down`, `left`, `right`, `f1` to `f11`, `kp_add`, `kp_subtract`, `plus`, `minus` and `equal`.

On Linux you can also use an XKB keysym name, the part of the name that follows `XKB_KEY_`, for keys kitty has no name of its own for. As a last resort a shortcut can use the raw hardware code of a key, such as `ctrl+0x3c`. To find a key's code, start `kitty --debug-input`, press the key, and read the `native_code` value in the log.

## Use kitty_mod in shortcuts

`kitty_mod` is a stand-in for the modifier combination that nearly all of kitty's default shortcuts use. It is `ctrl+shift` by default. You can use it in your own lines:

```
map kitty_mod+y new_tab_with_cwd
```

If you change it, for example with `kitty_mod ctrl+alt`, every default shortcut built on `kitty_mod` moves to the new modifiers at once.

## Free a key for the program running in kitty

If a default kitty shortcut clashes with a program you use, remove kitty's binding so the key reaches the program. Write a `map` line with the key and no action:

```
map kitty_mod+enter
```

Mapping a key to `no_op` has the same effect: kitty stops intercepting it. If you want the key press to vanish entirely, so that neither kitty nor the program acts on it, map it to `discard_event` instead.

## Start from an empty set of shortcuts

`clear_all_shortcuts yes` removes every shortcut defined before that line, including kitty's defaults. Put it at the top of `kitty.conf`, then add only the `map` lines you want. For mouse bindings the matching option is `clear_all_mouse_actions yes`.

## Browse all actions and their keys

Press `ctrl+shift+f3` to open the command palette. It lists every action kitty knows, shows the key bound to each, and lets you run any of them. This is the quickest way to find an action's exact name before writing a `map` line.

## Create a multi-key shortcut

A shortcut can be a sequence of key presses separated by `>`. You press the first key, release it, then press the next:

```
map ctrl+g>t new_tab
map ctrl+g>w new_window
map ctrl+g>1 change_font_size all 14
```

kitty's own defaults use this for the hints shortcuts (`ctrl+shift+p` followed by a letter) and background opacity (`ctrl+shift+a` followed by a letter).

`map_timeout` sets how long, in seconds, kitty waits for the next key of a sequence. The default `0.0` means no time limit. The timer restarts after every key that continues a valid sequence; when it expires, the keys typed so far are dropped.

## Build a keyboard mode

A keyboard mode is a set of shortcuts that only work after you enter the mode, similar to modal editors. `--new-mode NAME` makes a key enter the mode, and `--mode NAME` puts a shortcut inside it:

```
map --new-mode nav ctrl+shift+space
map --mode nav h neighboring_window left
map --mode nav l neighboring_window right
map --mode nav k neighboring_window up
map --mode nav j neighboring_window down
map --mode nav esc pop_keyboard_mode
```

The `pop_keyboard_mode` action leaves the current mode, and `push_keyboard_mode NAME` enters one from any shortcut. The name of the active mode is available as `{keyboard_mode}` in `tab_title_template`, so you can show it in the tab bar.

## Control how a keyboard mode behaves

Options on the `--new-mode` line change how the mode reacts:

| Option | Values | Effect |
|---|---|---|
| `--on-unknown` | `beep` (default), `ignore`, `end`, `passthrough` | What happens when you press a key with no binding in the mode |
| `--on-action` | `keep` (default), `end` | Whether the mode stays active after one of its actions runs |
| `--timeout` | seconds | Leave the mode after this long; overrides `map_timeout` |

For a one-shot mode that exits after each action and lets unknown keys through, you could write:

```
map --new-mode quick --on-action end --on-unknown passthrough ctrl+shift+space
```

## Make a shortcut apply only in some windows

`--when-focus-on EXPR` limits a shortcut to times when the focused window matches a search expression, such as a title or a user variable:

```
map --when-focus-on var:in_editor ctrl+shift+w no_op
```

Writing `--when-focus-on EXPR` with keys but no action removes the shortcut only while that condition holds. For multi-key sequences the condition belongs to the first key; there can be one condition per first key, and the last such line in the file wins.

## Keep shortcuts working on non-Latin keyboard layouts

`--allow-fallback` decides how kitty matches a shortcut when your keyboard layout produces different characters:

- `shifted` (the default for your own shortcuts) also matches the shifted version of the key.
- `ascii` matches the key in the same physical position on a US layout, but only when the key would type a character outside ASCII. Layouts such as Dvorak or Colemak are therefore unaffected.
- `none` requires an exact match.

You can combine values with commas. All of kitty's default letter shortcuts use `--allow-fallback=shifted,ascii`, so they keep working with Cyrillic, Greek and other non-Latin layouts.

## Run several actions from one key

The `combine` action runs actions one after another. Its first argument is a separator of your choosing, which then divides the actions:

```
map kitty_mod+o combine | new_tab | goto_layout grid
```

## Give an action a short name

`action_alias` defines a new name for an action with arguments. Aliases are expanded recursively, so one alias may use another.

```
action_alias here_window launch --cwd=current
map f8 here_window
map f9 here_window htop
```

The older `kitten_alias` does the same for kittens only; prefer `action_alias`.

## Run kittens and remote-control commands from a key

- `kitten NAME [args]` runs a built-in kitten or your own Python kitten file.
- `remote_control CMD ARGS` runs one `kitten @` command from a key press. This works even when remote control is disabled for programs. For example, `map f10 remote_control set-spacing padding=12`.
- `remote_control_script PATH` runs an executable script that itself calls `kitten @ ...`.

## Send keys or text to the program

- `send_key KEYS...` makes kitty pretend you pressed other keys. For instance, `map alt+w send_key ctrl+w` delivers `ctrl+w` to the program when you press `alt+w`.
- `send_text MODES TEXT` sends literal text. MODES selects when it applies: `normal`, `application`, `kitty`, a comma-separated combination, or `all`. Escapes in the text such as `\e` (escape) and `\r` (carriage return) are decoded.

```
map f12 send_text all git status\r
```

An old standalone `send_text` configuration line is still accepted and is converted into a `map` line.

## Useful actions that have no default key

These actions are worth binding yourself:

- `new_window_with_cwd`, `new_tab_with_cwd`, `new_os_window_with_cwd` open a window, tab or OS window in the current directory.
- `copy_or_interrupt`, `copy_and_clear_or_interrupt`, `copy_or_noop` are common choices to bind to `ctrl+c`.
- `copy_to_buffer NAME` and `paste_from_buffer NAME` use named private clipboards.
- `goto_tab N`, `select_tab`, `toggle_tab EXPR`, `goto_layout NAME`, `toggle_layout NAME`, `neighboring_window DIR`, `move_window DIR`, `resize_window ...`, `nth_window N`, `detach_window`, `detach_tab`, `close_other_windows_in_tab`, `close_os_window`, `quit`, `set_window_title`, `close_window_with_confirmation`, `signal_child SIG`, `show_context_menu` and `select_all`.
- `scroll_to_prompt N [CONTEXT_LINES]` jumps between shell prompts: a negative N goes up, positive goes down, `0` returns to the last visited prompt. It needs shell integration.
- `show_kitty_doc PAGE` opens a documentation page, such as `conf`.
- `kitty_shell` opens an interactive shell for controlling kitty in a `window`, `tab`, `overlay` or `os_window`.

## Clear the screen or scrollback with a key

`clear_terminal MODE TARGET` clears in different ways. MODE is one of `reset`, `clear`, `scrollback`, `scroll`, `to_cursor`, `to_cursor_scroll` or `last_command`; TARGET is `active` for the current window or `all` for every window.

```
map ctrl+shift+k clear_terminal scrollback active
```

The default `ctrl+shift+delete` runs `clear_terminal reset active`.

## Change the font size with your own keys

`change_font_size` takes a scope and an amount. The scope is `all` for every window or `current` for the focused one. The amount can be `+N`, `-N`, `*N` or `/N` for relative changes, a bare number for an absolute size, or `0` to go back to the size in `kitty.conf`.

```
map ctrl+shift+f9 change_font_size current 20
map ctrl+alt+equal change_font_size current *1.25
```

Some older examples use `set_font_size`; that is a legacy name and not part of the listed actions in 0.48.2, so use `change_font_size`.

## Change background opacity with keys

`set_background_opacity` accepts `+0.1`, `-0.1`, an absolute value such as `0.8` or `1`, or `default`. It only works if `kitty.conf` had `dynamic_background_opacity yes` when kitty started. The defaults are the sequences `ctrl+shift+a` then `m` (more opaque), `l` (less opaque), `1` (fully opaque) and `d` (back to the configured value).

## Bind actions to mouse buttons

A mouse binding is one `mouse_map` line:

```
mouse_map BUTTON EVENT MODES ACTION
```

- **BUTTON** is `left`, `middle`, `right`, or `b1` to `b8`, optionally with modifiers such as `ctrl+alt+right`.
- **EVENT** is `press`, `release`, `doublepress`, `triplepress`, `click` or `doubleclick`. `click` and `doubleclick` wait for the `click_interval` to pass before firing, so they react a little later.
- **MODES** is `grabbed`, `ungrabbed` or `grabbed,ungrabbed`. A window is "grabbed" when the program inside has asked to receive mouse events, as many editors and file managers do.

Example: paste the clipboard on a middle click even inside mouse-aware programs, using shift:

```
mouse_map shift+middle release grabbed,ungrabbed paste_from_clipboard
```

## Remove a mouse binding

Leave out the action to remove a binding. For instance, to stop a plain left click from opening URLs:

```
mouse_map left click ungrabbed
```

When you release the button that began a selection, the selection finishes and no release event is dispatched for that button.

## Mouse actions you can bind

These actions are meant for `mouse_map`:

- `mouse_handle_click` with any of `selection`, `link` and `prompt`.
- `mouse_selection` with one of `normal`, `rectangle`, `word`, `line`, `line_from_begin`, `line_from_point` or `extend`.
- `mouse_click_url`, `mouse_click_url_or_select`.
- `mouse_show_command_output`, `mouse_select_command_output` (need shell integration).
- `paste_selection`, `paste_selection_or_clipboard`.

## Debug a shortcut that does not work

1. Press `ctrl+shift+f6` (`debug_config`) to see your effective configuration, including which shortcuts are active.
2. Start `kitty --debug-input` and press the key; the log shows each key event and what kitty did with it.
3. Run `kitten show-key` to see the bytes a key sends to programs, or `kitten show-key -m kitty` to see it in kitty's keyboard protocol.

## Default clipboard shortcuts

All tables assume `kitty_mod` is `ctrl+shift`.

| Keys | Action |
|---|---|
| `ctrl+shift+c` | `copy_to_clipboard` |
| `ctrl+shift+v` | `paste_from_clipboard` |
| `ctrl+shift+s` | `paste_from_selection` |
| `shift+insert` | `paste_from_selection` |
| `ctrl+shift+o` | `pass_selection_to_program` |

## Default scrolling shortcuts

Scrolling keys act on the main screen only. Full-screen programs that use the alternate screen, such as editors, receive the keys themselves. The `smooth` argument animates line scrolling; leave it out for instant scrolling.

| Keys | Action |
|---|---|
| `ctrl+shift+up` or `ctrl+shift+k` | `scroll_line_up smooth` |
| `ctrl+shift+down` or `ctrl+shift+j` | `scroll_line_down smooth` |
| `ctrl+shift+page_up` | `scroll_page_up` |
| `ctrl+shift+page_down` | `scroll_page_down` |
| `ctrl+shift+home` | `scroll_home` |
| `ctrl+shift+end` | `scroll_end` |
| `ctrl+shift+z` | `scroll_to_prompt -1` (previous prompt) |
| `ctrl+shift+x` | `scroll_to_prompt 1` (next prompt) |
| `ctrl+shift+h` | `show_scrollback` |
| `ctrl+shift+g` | `show_last_command_output` |
| `ctrl+shift+/` | `search_scrollback` |

## Default window shortcuts

| Keys | Action |
|---|---|
| `ctrl+shift+enter` | `new_window` |
| `ctrl+shift+n` | `new_os_window` |
| `ctrl+shift+w` | `close_window` |
| `ctrl+shift+]` | `next_window` |
| `ctrl+shift+[` | `previous_window` |
| `ctrl+shift+f` | `move_window_forward` |
| `ctrl+shift+b` | `move_window_backward` |
| ``ctrl+shift+` `` | `move_window_to_top` |
| `ctrl+shift+r` | `start_resizing_window` |
| `ctrl+shift+1` ... `ctrl+shift+9` | `first_window` ... `ninth_window` |
| `ctrl+shift+0` | `tenth_window` |
| `ctrl+shift+f7` | `focus_visible_window` |
| `ctrl+shift+f8` | `swap_with_window` |

## Default tab and layout shortcuts

| Keys | Action |
|---|---|
| `ctrl+shift+right` or `ctrl+tab` | `next_tab` |
| `ctrl+shift+left` or `ctrl+shift+tab` | `previous_tab` |
| `ctrl+shift+t` | `new_tab` |
| `ctrl+shift+q` | `close_tab` |
| `ctrl+shift+.` | `move_tab_forward` |
| `ctrl+shift+,` | `move_tab_backward` |
| `ctrl+shift+alt+t` | `set_tab_title` |
| `ctrl+shift+l` | `next_layout` |

## Default font size shortcuts

| Keys | Action |
|---|---|
| `ctrl+shift+equal`, `ctrl+shift+plus` or `ctrl+shift+kp_add` | `change_font_size all +2.0` |
| `ctrl+shift+minus` or `ctrl+shift+kp_subtract` | `change_font_size all -2.0` |
| `ctrl+shift+backspace` | `change_font_size all 0` |

## Default shortcuts for selecting visible text

These use the hints and file-chooser kittens. Keys written `a>b` are sequences: press the first, then the second.

| Keys | Action | What it does |
|---|---|---|
| `ctrl+shift+e` | `open_url_with_hints` | Pick a URL on screen and open it |
| `ctrl+shift+p>f` | `kitten hints --type path --program -` | Insert a path from the screen |
| `ctrl+shift+p>shift+f` | `kitten hints --type path` | Open a path from the screen |
| `ctrl+shift+p>c` | `kitten choose-files` | Insert a chosen file |
| `ctrl+shift+p>d` | `kitten choose-files --mode=dir` | Insert a chosen directory |
| `ctrl+shift+p>l` | `kitten hints --type line --program -` | Insert a line from the screen |
| `ctrl+shift+p>w` | `kitten hints --type word --program -` | Insert a word from the screen |
| `ctrl+shift+p>h` | `kitten hints --type hash --program -` | Insert a hash from the screen |
| `ctrl+shift+p>n` | `kitten hints --type linenum` | Go to a file at a line number |
| `ctrl+shift+p>y` | `kitten hints --type hyperlink` | Open a hyperlink from the screen |

## Other default shortcuts

| Keys | Action |
|---|---|
| `ctrl+shift+f1` | `show_kitty_doc overview` |
| `ctrl+shift+f2` | `edit_config_file` |
| `ctrl+shift+f3` | `command_palette` |
| `ctrl+shift+f5` | `load_config_file` |
| `ctrl+shift+f6` | `debug_config` |
| `ctrl+shift+f10` | `toggle_maximized` |
| `ctrl+shift+f11` | `toggle_fullscreen` |
| `ctrl+shift+u` | `kitten unicode_input` |
| `ctrl+shift+escape` | `kitty_shell window` |
| `ctrl+shift+a>m` | `set_background_opacity +0.1` |
| `ctrl+shift+a>l` | `set_background_opacity -0.1` |
| `ctrl+shift+a>1` | `set_background_opacity 1` |
| `ctrl+shift+a>d` | `set_background_opacity default` |
| `ctrl+shift+delete` | `clear_terminal reset active` |

## Default mouse bindings for ordinary windows

These apply when the program in the window has not grabbed the mouse ("ungrabbed").

| Button and event | Action |
|---|---|
| `left` click | `mouse_handle_click selection link prompt` |
| `left` press | `mouse_selection normal` |
| `left` double press | `mouse_selection word` |
| `left` triple press | `mouse_selection line` |
| `alt+left` triple press | `mouse_selection line_from_begin` |
| `ctrl+alt+left` press | `mouse_selection rectangle` |
| `ctrl+alt+left` triple press | `mouse_selection line_from_point` |
| `right` press | `mouse_selection extend` |
| `shift+left` press | `mouse_selection extend` |
| `middle` release | `paste_from_selection` |
| `ctrl+shift+right` press | `mouse_show_command_output` |

## Default mouse bindings that work in mouse-aware programs

These use `shift` so that they work even when the program has grabbed the mouse.

| Button and event | Modes | Action |
|---|---|---|
| `shift+left` click | grabbed, ungrabbed | `mouse_handle_click selection link prompt` |
| `shift+left` press | grabbed | `mouse_selection normal` |
| `shift+left` double press | grabbed, ungrabbed | `mouse_selection word` |
| `shift+left` triple press | grabbed, ungrabbed | `mouse_selection line` |
| `shift+alt+left` triple press | grabbed, ungrabbed | `mouse_selection line_from_begin` |
| `ctrl+shift+alt+left` press | grabbed, ungrabbed | `mouse_selection rectangle` |
| `ctrl+shift+alt+left` triple press | grabbed, ungrabbed | `mouse_selection line_from_point` |
| `shift+right` press | grabbed, ungrabbed | `mouse_selection extend` |
| `shift+middle` release | grabbed, ungrabbed | `paste_selection` |
| `shift+middle` press | grabbed | `discard_event` |
| `ctrl+shift+left` release | grabbed, ungrabbed | `mouse_handle_click link` |
| `ctrl+shift+left` press | grabbed | `discard_event` |

## In Kilix: binding Kilix actions

Kilix adds the actions `kilix_show_start_menu`, `kilix_windows_key`, `kilix_toggle_synchronized_input`, `kilix_close_persistent_window` and `kilix_show_memory_widget`. kitty's own configuration gives them no default Linux keys, so use `map` to put one on a key, for example `map ctrl+shift+i kilix_toggle_synchronized_input`.

## See also

- `01-getting-started.md` - kitty's building blocks and first steps
- `02-command-line.md` - starting kitty and its command-line options
- `03-configuration.md` - the `kitty.conf` file and its options
- `05-tabs-windows-layouts.md` - managing tabs, windows and layouts
- `06-launch-and-sessions.md` - the `launch` action and session files
