# Copy, paste, selections, URLs and hyperlinks

This page is about moving text in and out of kitty and following links. It covers the default copy and paste keys, the primary selection, named private buffers, the mouse bindings for selecting text, clipboard safety options (what programs may read or write, and what gets checked before a paste), how kitty spots URLs and opens them, OSC 8 hyperlinks, and the two configuration files that decide what happens when you click a link (`open-actions.conf`) or open a file with kitty (`launch-actions.conf`). Kilix adds a right-click context menu, which is described too.

## Copy and paste with the keyboard

Default keys on Linux:

| Keys | Action | What it does |
|---|---|---|
| `ctrl+shift+c` | `copy_to_clipboard` | copies the selection to the clipboard |
| `ctrl+shift+v` | `paste_from_clipboard` | pastes the clipboard |
| `ctrl+shift+s` | `paste_from_selection` | pastes the primary selection |
| `shift+insert` | `paste_from_selection` | pastes the primary selection |
| `ctrl+shift+o` | `pass_selection_to_program` | hands the selection to a program (opens it as a URL by default) |

Plain `ctrl+c` and `ctrl+v` are left for the programs running in the terminal, where `ctrl+c` interrupts.

## Make `ctrl+c` copy when text is selected

If you want `ctrl+c` to copy when something is selected and interrupt otherwise, use `copy_or_interrupt`:

```
map ctrl+c copy_or_interrupt
```

Related actions:

- `copy_and_clear_or_interrupt` - copies and then clears the selection, or interrupts.
- `copy_or_noop` - copies if there is a selection; otherwise the key goes to the program unchanged.
- `copy_ansi_to_clipboard` - copies the selection with its colour and style codes.
- `copy_selection_or_last_command_output` - copies the selection, or, if there is none, the output of the last command that produced output (needs shell integration).
- `copy_last_command_output` - copies the last non-empty command output (needs shell integration).

## Paste fixed text from a key

The `paste` action pastes the text you give it. C-style escapes such as `\n` are decoded:

```
map ctrl+alt+m paste me@example.org
```

## Use the primary selection

On Linux (X11 and Wayland) selecting text with the mouse automatically puts it in the primary selection, separate from the clipboard. Middle-click pastes it. `paste_from_selection` pastes the primary selection if there is one, otherwise the clipboard.

## Copy selected text automatically

`copy_on_select` (default `no`) copies every mouse selection somewhere without a key press:

```
copy_on_select clipboard
```

- `clipboard` copies each selection to the system clipboard.
- Any other name, such as `a1`, copies it to a private buffer of that name. Paste it with `map KEY paste_from_buffer a1`.

Be aware that anything on the system clipboard can be read by other applications, including web pages in your browser.

## Keep several private copy buffers

`copy_to_buffer NAME` and `paste_from_buffer NAME` store and paste text in named buffers private to kitty. Any name works. Two names are special: `clipboard` means the system clipboard and `primary` means the primary selection.

```
map ctrl+alt+1 copy_to_buffer one
map ctrl+alt+2 paste_from_buffer one
```

## Select text with the mouse

Default mouse bindings:

- Left press and drag: start a selection.
- `ctrl+alt` + left press: rectangular (block) selection.
- Double-click: select a word. Triple-click: select a line.
- `alt` + triple-click: select from the start of the line. `ctrl+alt` + triple-click: select from the click point to the end of the line.
- `shift` + left press, or right press: extend the selection.
- Middle-click release: paste the primary selection.

When a program such as an editor has grabbed the mouse, hold `shift` to make kitty handle the click instead (for example `shift` + middle-click to paste).

`clear_selection` clears the selection, and `select_all` selects everything, including the scrollback.

**In Kilix:** right-click opens a context menu instead of extending the selection. See the next section.

## In Kilix: the right-click context menu

Kilix adds the action `show_context_menu`. It opens a small menu with Copy, Paste, Select all and Clear selection; the keys `c`, `p`, `s` and `l` choose those entries. Kilix's shipped configuration, which the `kilix` launcher loads, binds it like this:

```
mouse_map right press ungrabbed show_context_menu
mouse_map ctrl+shift+right press grabbed show_context_menu
```

This replaces upstream kitty's behaviour, where right-click extends the selection. To get the upstream behaviour back, bind right press to another action in your own `kitty.conf`. This action does not exist in upstream kitty.

## Control trailing spaces and word boundaries

- `strip_trailing_spaces` (default `never`): `always` removes trailing spaces from copied text; `smart` removes them for normal selections but not for rectangular ones.
- `select_by_word_characters` (default `@-./_~?&=%+#`) lists characters that count as part of a word on double-click, in addition to Unicode letters and digits. `select_by_word_characters_forward` (default empty, meaning the same set) can use a different set when extending forward.
- `click_interval` (default `-1.0`) is the maximum gap between clicks of a double-click; negative means the system setting, or 0.5 seconds.
- `selection_foreground` (`#000000`) and `selection_background` (`#fffacd`) colour the selection. Setting both to `none` uses reverse video.

## Decide what programs may do with the clipboard

Programs can read and write the clipboard with escape codes (OSC 52 for plain text, and kitty's OSC 5522 extension for any MIME type such as images). `clipboard_control` sets what is permitted. The default is:

```
clipboard_control write-clipboard write-primary read-clipboard-ask read-primary-ask
```

So programs may write freely but must ask before reading. The available words are `write-clipboard`, `read-clipboard`, `write-primary`, `read-primary`, `read-clipboard-ask` and `read-primary-ask`. Allowing reads without asking lets any program, including one on a remote machine over SSH, see your clipboard.

`clipboard_max_size` (default `512`, in megabytes; `0` means no limit) caps how much data a program may put on the clipboard.

## Check what gets pasted

`paste_actions` decides what kitty does to text before pasting (and to text dropped with drag and drop). The default is `quote-urls-at-prompt,confirm`. Available words, comma separated:

- `quote-urls-at-prompt` - quotes a pasted URL when the cursor is at a shell prompt (needs shell integration).
- `confirm` - asks first if the text contains terminal control codes.
- `confirm-if-large` - asks first if the text is larger than 16 KB.
- `replace-dangerous-control-codes` - silently removes dangerous control codes.
- `replace-newline` - silently replaces newlines.
- `filter` - runs `filter_paste(text)` from `paste-actions.py` in the kitty config directory and pastes whatever it returns.
- `no-op` - does nothing.

```
paste_actions quote-urls-at-prompt,confirm,confirm-if-large
```

## Send the selection to a program

`pass_selection_to_program` (default `ctrl+shift+o`) gives the selected text to a program, started in the working directory of the window's program. With no program named, the selection is opened as a URL.

```
map ctrl+alt+g pass_selection_to_program firefox
```

## How kitty detects URLs

With `detect_urls yes` (the default), a URL under the mouse is underlined and the pointer becomes a hand. Even with `detect_urls no`, URLs can still be clicked.

- `url_prefixes` sets which schemes count as URLs. Default: `file ftp ftps gemini git gopher http https irc ircs kitty mailto news sftp ssh`.
- `url_excluded_characters` (default empty) adds characters that end a URL. By default a newline inside a URL is allowed and then removed, which helps with mail clients that hard-wrap long links; add `\n` here to stop that.
- `url_color` (default `#0087bd`) and `url_style` (default `curly`) set the underline. Styles: `none`, `straight` (or `single`), `double`, `curly`, `dotted`, `dashed`.

## Open URLs with the mouse or keyboard

- Plain left-click on a URL opens it, as long as no text is selected.
- `ctrl+shift` + left-click opens it even inside programs that grab the mouse.
- `ctrl+shift+e` (action `open_url_with_hints`) shows keyboard hints over every URL on screen; type a hint to open that URL.
- `ctrl+shift+p` then `y` does the same for OSC 8 hyperlinks.
- The `open_url URL` action opens a specific URL, handy in mappings.

The opener is chosen by `open_url_with`. Its default, `default`, first checks `open-actions.conf` and then falls back to the system handler, `xdg-open` on Linux. Any other value is used as a command:

```
open_url_with firefox --new-tab
```

## Control OSC 8 hyperlinks

Programs can print text that links to a hidden target, for example `ls --hyperlink=auto`, gcc, systemd tools and the hyperlinked-grep kitten.

- `allow_hyperlinks` (default `yes`): `no` ignores these links; `ask` asks for confirmation before opening one.
- `underline_hyperlinks` (default `hover`): `hover`, `always` or `never`. `always` applies only to real OSC 8 links, not to detected URLs. It uses `url_style` and `url_color`, and after a reload it affects only newly received text.
- `show_hyperlink_targets` (default `never`): `always` shows the link target when hovering; a modifier name (`ctrl`, `alt`, `shift`, or `cmd`, which is Super on Linux) shows it only while that key is held.

## Choose what happens when you click a link: `open-actions.conf`

When `open_url_with` is `default`, kitty reads `~/.config/kitty/open-actions.conf` to decide how to open things. The file is a list of entries separated by blank lines. Each entry has one or more matching lines and one or more `action` lines. The first entry whose matching lines all apply wins, so put specific entries before general ones.

Matching lines:

- `protocol` - comma list, such as `http, https` or `file`.
- `url` - a regular expression tested against the whole URL (unquoted).
- `fragment_matches` - a regular expression tested against the part after `#`.
- `mime` - comma list of MIME types, globs allowed (`image/*`). The type is guessed from the file extension, not the content. Directories are `inode/directory`. Add your own types in `mime.types` in the kitty config directory, for example `text/plain rst md`.
- `ext` - comma list of extensions, such as `jpeg, tar.gz`.
- `file` - a shell glob for the file name.

An `action` line holds any mappable action, most often `launch`. Several `action` lines run in order, and `action_alias` names work.

## Variables in open actions

These can be used in actions as `$NAME` or `${NAME}`: `URL`, `FILE_PATH` (the unquoted path), `FILE` (the file name), `FRAGMENT`, `NETLOC` (the host), `URL_PATH` (path, query and fragment, still quoted), `EDITOR`, `SHELL`, and any normal environment variable.

Example: open log files in a pager in a new tab, open images with the icat kitten, and open everything else normally:

```
protocol file
ext log
action launch --type=tab less +G -- ${FILE_PATH}

protocol file
mime image/*
action launch --type=overlay kitten icat --hold -- ${FILE_PATH}
```

Example: make `file://path#123` links from grep tools open the editor at line 123:

```
protocol file
fragment_matches [0-9]+
action launch --type=overlay $EDITOR +${FRAGMENT} ${FILE_PATH}
```

## Open files with kitty: `launch-actions.conf`

`kitty +open FILE_OR_URL` and desktop "open with kitty" file associations use `launch-actions.conf` in the kitty config directory. It uses the same format as `open-actions.conf`, and your entries take priority over the built-in ones. `kitty +open` also accepts normal kitty options such as `--class`.

Built-in behaviour, in order:

1. Shell scripts (`.sh`, `.command`, `.tool`) run in a new OS window after confirmation, and the window stays open afterwards.
2. `.fish`, `.bash` and `.zsh` files run with that shell, with the same confirmation.
3. Directories open a new OS window in that directory.
4. Executables ask for confirmation, run, and stay open.
5. Text files open in `$EDITOR` in a new OS window.
6. Images open with `kitten icat --hold` in a new OS window.
7. `ssh` URLs run `ssh` to that address in a new OS window.

The confirmation setting for scripts can be `confirm-always` (the built-in choice), `confirm-never` or `confirm-if-needed`.

## Where opened programs get their environment

Programs started to open a URL receive `KITTY_LISTEN_ON` when kitty is listening for remote control, and `XDG_ACTIVATION_TOKEN` when one is available, which helps Wayland give focus to the new window.

## See also

- 01-getting-started.md
- 02-command-line.md
- 03-configuration.md
- 04-keyboard-and-mouse.md
- 05-tabs-windows-layouts.md
- 06-launch-and-sessions.md
- 07-remote-control.md
- 08-shell-integration.md
- 09-scrollback-search-marks.md
- 11-kittens.md
- 12-troubleshooting.md
