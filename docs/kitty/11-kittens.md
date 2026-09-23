# Kittens: kitty's built-in helper programs

Kittens are small programs that come with kitty and use its special features: showing images, comparing files side by side, picking text on screen with the keyboard, logging in over SSH with everything set up, changing themes and fonts, copying files through the terminal, sending desktop notifications, and more. Most are run from the shell as `kitten NAME`, and many can also be bound to keys in `kitty.conf`. This page explains how to run kittens and then gives one section per kitten with what it is for, how to start it, its main options and any default shortcut. Kilix adds one kitten of its own, `browse`.

## Run a kitten

There are three ways:

- From a shell: `kitten NAME [options]`. Names with hyphens are the main form (`show-key`, `unicode-input`, `query-terminal`), but underscore spellings such as `show_key` are accepted too.
- Kittens written only in Python (such as `broadcast`) run as `kitty +kitten NAME`.
- From a key mapping: `map KEY kitten NAME ARGS`.

The kittens in this build are: `@` (remote control, see 07-remote-control.md), `ask`, `browse` (Kilix), `choose-files`, `choose-fonts`, `clipboard`, `command-palette`, `desktop-ui`, `diff`, `dnd`, `edit-in-kitty`, `hints`, `hyperlinked-grep`, `icat`, `mouse-demo`, `notify`, `panel`, `query-terminal`, `quick-access-terminal`, `run-shell`, `show-key`, `ssh`, `themes`, `transfer`, `unicode-input` and `update-self`. `broadcast` is Python-only, and `remote_file` is used internally.

## icat: show images in the terminal

`kitten icat` displays images right in the terminal. Give it files, directories (searched recursively) or `http`, `https` or `ftp` URLs, which it downloads. If its standard input is not a terminal, it reads an image from there.

```
kitten icat photo.jpg
curl -s https://example.com/chart.png | kitten icat
```

A handy alias is `alias icat="kitten icat"`.

Main options:

- `--place WxH@LxT` - draw the image inside a box W cells wide and H high, with its top-left corner at column L, row T. The cursor is left at the image's top-left corner.
- `--align center|left|right` (default `center`), `--fit width|both|height|none` (default `width`), `--scale-up` to enlarge small images.
- `--clear` removes images from the screen (not supported inside tmux); `--clear-all` also removes them from the scrollback.
- `--hold` waits for a key press before exiting.
- `--z-index` / `-z` - a negative value draws the image under the text.
- `--loop` / `-l` - how many times to play animations; `-1` loops forever.
- `--transfer-mode detect|file|memory|stream` (default `detect`). `file` and `memory` fail across SSH.
- `--passthrough detect|none|tmux` and `--unicode-placeholder` for tmux and editors. Inside tmux, passthrough is detected automatically and turns on Unicode placeholders.
- `--detect-support` exits with 0 if the terminal can show images and 1 if not.
- Also: `--engine auto|builtin|magick`, `--background COLOR`, `--mirror`, `-n` (no newline after the image), `--use-window-size`, `--print-window-size`, `--image-id`.

icat has no default shortcut. kitty's default open action for images uses it.

## diff: compare files side by side

`kitten diff LEFT RIGHT` shows a side-by-side diff with syntax highlighting. It can compare directories (recursively), show differences between images, and read remote files written as `ssh:HOST:PATH`.

```
kitten diff old.py new.py
kitten diff ~/project-v1 ~/project-v2
```

Options: `--context N` (lines of context; the default `-1` uses the config file value), `--config PATH`, and `--override key=value` (`-o`). Its config file is `diff.conf` in the kitty config directory.

Keys inside the viewer:

- `q` quits; `j`, `k` and the arrow keys move one line.
- `Page Up`, `Page Down`, `space`, `ctrl+f`, `ctrl+b` move by a page; `ctrl+d`, `ctrl+u` by half a page; `Home` and `End` go to either end.
- `n` and `p` jump to the next and previous change.
- `+` and `-` change the context; `a` shows all context; `=` returns to the default.
- `/` and `?` search; `>` or `.` goes to the next match, `<` or `,` to the previous one; `Esc` clears the search.
- `y` copies the selection; `ctrl+c` copies or exits.

The diff kitten needs kitty's graphics and keyboard features, so it only works in kitty (and Kilix).

## Use the diff kitten with git

Add this to `~/.gitconfig`:

```
[diff]
    tool = kitty
[difftool]
    prompt = false
    trustExitCode = true
[difftool "kitty"]
    cmd = kitten diff $LOCAL $REMOTE
```

Then compare the working tree with `git difftool --no-symlinks --dir-diff`.

## hints: pick text on screen with the keyboard

The hints kitten labels matching items on screen (URLs, paths, words and so on). Type a label and the item is opened, pasted or copied. By default it looks for URLs.

Default shortcuts:

| Keys | Result |
|---|---|
| `ctrl+shift+e` | open a URL |
| `ctrl+shift+p`, then `f` | insert a path at the cursor |
| `ctrl+shift+p`, then `shift+f` | open a path |
| `ctrl+shift+p`, then `l` | insert a line |
| `ctrl+shift+p`, then `w` | insert a word |
| `ctrl+shift+p`, then `h` | insert a hash (for example a git commit id) |
| `ctrl+shift+p`, then `n` | open a `file:line` reference in your editor |
| `ctrl+shift+p`, then `y` | open an OSC 8 hyperlink |

## hints options and custom mappings

- `--type` - `url` (default), `hash`, `hyperlink`, `ip`, `line`, `linenum`, `path`, `regex` or `word`. With `regex`, give the pattern with `--regex`.
- `--program` - what to do with the choice: `-` pastes it into the terminal, `@` copies to the clipboard, `*` copies to the primary selection, `@NAME` copies to a named buffer, `default` opens it with the system opener. Anything else is run as a command with the choice added.
- `--multiple` picks several items (press `Esc` to finish); `--multiple-joiner` sets how they are joined (`space`, `newline`, `empty`, `json`, `auto`, or an index).
- `--minimum-match-length` (default 3), `--alphabet`, `--ascending`, `--hints-offset`, `--prefix-free`, `--add-trailing-space auto|always|never`, `--linenum-action`, `--customize-processing FILE.py`, and colour options `--hints-foreground-color` and `--hints-background-color`.

Examples:

```
map ctrl+shift+p>i kitten hints --type ip --program @
map ctrl+shift+p>t kitten hints --type regex --regex 'TICKET-[0-9]+' --program -
```

## ssh: log in to other machines with everything set up

`kitten ssh` accepts the same arguments as `ssh` and can replace it for interactive use:

```
kitten ssh me@server.example.com
alias s="kitten ssh"
```

Without any setup on the remote machine, it:

- copies kitty's terminfo, so `xterm-kitty` programs work,
- turns on shell integration in the remote shell,
- reuses one connection for several sessions (faster new logins),
- can copy files and set environment variables on login,
- can forward remote control (optional).

With `new_window_with_cwd` mapped, pressing that key opens a new window already logged in to the same host and directory.

## Configure the ssh kitten with `ssh.conf`

Settings go in `~/.config/kitty/ssh.conf`, grouped under `hostname PATTERN` lines (globs, `user@host`, several patterns separated by spaces). Since 0.28.0, a block does not inherit from earlier blocks.

```
hostname *.lab.example.com
color_scheme Solarized Dark
env EDITOR=vim
copy .vimrc

hostname backup
share_connections no
```

Settings (defaults in brackets where known): `interpreter` (`sh`; prefer `python` on BSD hosts), `remote_dir` (`.local/share/kitty-ssh-kitten`), `copy` (with `--dest`, `--glob`, `--exclude`), `shell_integration` (`inherited`), `login_shell` (empty means the account's own), `env`, `cwd`, `color_scheme` (a theme name or a `.conf` file), `remote_kitty` (`if-needed`, `no` or `yes`), `share_connections` (`yes`), `askpass` (`unless-set`, `ssh` or `native`), `delegate CMD` (skip the kitten for this host and run CMD), `forward_remote_control` (`no`), `password`, `totp_secret`, `totp_digits` (`6`) and `totp_period` (`30`).

Override one setting for a single login: `kitten ssh --kitten color_scheme=Nord HOST`.

Notes:

- `forward_remote_control` is a security risk and does not work with abstract sockets.
- With `remote_kitty`, a small script downloads `kitten` on the remote host on first use; update it later with `kitten update-self`.
- The `close_shared_ssh_connections` action closes all shared connections.
- Inside tmux, stale `KITTY_PID` or `KITTY_WINDOW_ID` values can make it fail.

## themes: change the colour theme

Run `kitten themes` to browse, search and preview themes interactively, or name one directly:

```
kitten themes "Gruvbox Dark"
```

The kitten writes the theme to `current-theme.conf` in the config directory, adds `include current-theme.conf` to `kitty.conf`, and comments out colour lines already there.

Options: `--reload-in parent|all|none` (default `parent`), `--dump-theme` (print the theme instead of applying it), `--config-file-name` (default `kitty.conf`) and `--cache-age DAYS` (default 1).

## Follow the desktop's light or dark mode

Since kitty 0.38.0 you can save a theme as the dark, light or no-preference theme from the themes kitten. These are stored as `dark-theme.auto.conf`, `light-theme.auto.conf` and `no-preference-theme.auto.conf`, and kitty switches between them as the system colour scheme changes. When present, these files win over every other colour setting and background image, including `--override`.

## unicode_input: type any character

Press `ctrl+shift+u` to insert any Unicode character. Four modes:

- **Code:** type the hex code point, such as `2716`.
- **Name:** search by name.
- **Emoticons.**
- **Favorites.**

Switch modes with `F1`-`F4`, `ctrl+1`-`ctrl+4`, `ctrl+[` and `ctrl+]`, or `ctrl+tab` and `ctrl+shift+tab`. Options: `--tab previous|code|emoticons|favorites|name` (default `previous`) and `--emoji-variation none|graphic|text`.

## transfer: copy files through the terminal

`kitten transfer` copies files over the terminal connection itself, so no separate SSH file transfer is needed. Run it on the remote side, for example after logging in with `kitten ssh`.

```
kitten transfer remote-report.pdf Downloads/report.pdf
kitten transfer --direction=upload Documents/notes.txt notes.txt
```

In the first line, `remote-report.pdf` is found in the remote current directory and saved as `Downloads/report.pdf` under your local home directory. In the second, `Documents/notes.txt` is taken from your local home directory and written to `notes.txt` in the remote current directory.

- By default files are downloaded from the remote side to your machine. `--direction=upload` (or `send`) goes the other way; the choices are `download`, `receive`, `send` and `upload`.
- With several sources, the destination must be an existing directory.
- Relative paths are relative to the current directory where the kitten runs, and to your home directory on the other side.
- Options: `--confirm-paths` (`-c`), `--transmit-deltas` (`-x`) for rsync-style updates, `--compress auto|always|never`, `--mode normal|mirror`, and `--permissions-bypass PASSWORD` (`-p`) to skip kitty's confirmation popup.
- Directories, symbolic links and hard links are handled.

## show_key: see what a key sends

`kitten show-key` prints what kitty sends for each key you press, which helps when a shortcut is not working. `-m` picks the keyboard mode: `normal` (default), `application`, `kitty` or `unchanged`.

```
kitten show-key -m kitty
```

See 12-troubleshooting.md for how to read the result.

## clipboard: use the clipboard from the command line

`kitten clipboard` reads and writes the clipboard, and works over SSH.

```
echo "hello" | kitten clipboard
kitten clipboard --get-clipboard > saved.txt
kitten clipboard -g -m .
```

- With no file arguments, it copies standard input to the clipboard; `-g` (`--get-clipboard`) prints the clipboard.
- With file arguments, it copies files of given MIME types (such as images) to or from the clipboard. `-m .` together with `-g` lists the MIME types available.
- Options: `-p` (`--use-primary`), `-m` (`--mime`), `-a` (`--alias`), `--wait-for-completion`, `--password`, `--human-name`.

Reading the clipboard triggers a permission prompt according to `clipboard_control` (see 10-clipboard-and-links.md).

## broadcast: type into many windows at once

The broadcast kitten sends what you type to many windows at the same time. It needs remote control, so start it through `launch` with that permission:

```
map f9 launch --allow-remote-control kitty +kitten broadcast
map f10 launch --allow-remote-control kitty +kitten broadcast --match-tab state:focused
```

By default it types into every window. Narrow the targets with `--match` (`-m`) or `--match-tab` (`-t`), using the matching syntax from 07-remote-control.md. Press `ctrl+esc` to stop, and `ctrl+alt+esc` to hide or show what you type (useful for passwords).

## hyperlinked_grep: clickable search results

`kitten hyperlinked-grep PATTERN [rg options]` runs ripgrep (`rg` must be installed) and turns results into hyperlinks. A suggested alias is `hg`. Available since kitty 0.19.0.

To make clicks open your editor at the right line, add to `open-actions.conf`:

```
protocol file
fragment_matches [0-9]+
action launch --type=overlay $EDITOR +${FRAGMENT} ${FILE_PATH}
```

Open a result with `ctrl+shift` + left-click, or from the keyboard with `ctrl+shift+p` then `y`.

`--kitten hyperlink=...` chooses which parts become links: `matching_lines`, `context_lines`, `file_headers` or `none` (plain ripgrep output). By default all three parts are linked. Newer ripgrep releases (after version 13) can do this themselves with `--hyperlink-format=kitty`, which makes the kitten optional.

## choose-fonts: pick fonts with previews

`kitten choose-fonts` lets you browse installed fonts with live previews and writes your choice to `kitty.conf`. Options: `--reload-in parent|all|none` and `--config-file-name`. It has no default shortcut. In 0.48.2, `kitty +list-fonts` simply starts this kitten.

## notify: send desktop notifications

`kitten notify TITLE [BODY...]` shows a desktop notification, and works from remote machines over SSH.

```
make && kitten notify "Build finished" "All targets built"
kitten notify -u critical -b Retry -b Cancel "Deploy failed"
```

Options: `--icon` (`-n`), `--icon-path` (`-p`), `--app-name` (`-a`, default `kitten-notify`), `--button` (`-b`, repeatable), `--urgency` (`-u` `normal|critical|low`), `--expire-after` (`-e`), `--sound-name` (`-s`), `--type` (`-t`), `--identifier` (`-i`), `--print-identifier` (`-P`), `--wait-for-completion` (`-w`) and `--only-print-escape-code`. Running it with `-i ID` and no title closes that notification.

The `filter_notification` option in `kitty.conf` can filter incoming notifications by `title`, `body`, `app` or `type`.

## panel: run a program as a desktop panel

`kitten panel [options] [command ...]` shows a terminal program as a panel, dock, desktop background or overlay drawn by kitty.

```
kitten panel --edge=bottom --lines=2 htop
```

Options include `--edge` (`top` by default, also `bottom`, `left`, `right`, `background`, `center`, `center-sized`, `none`), `--lines` and `--columns` (default 1), margins, `--layer` (Wayland), `--focus-policy not-allowed|exclusive|on-demand`, `--hide-on-focus-loss`, `--grab-keyboard`, `--exclusive-zone`, `--output-name`, `--app-id` (default `kitty-panel`), `--single-instance`, `--toggle-visibility`, `--start-as-hidden`, `--detach` and `--listen-on`.

On Wayland it needs the wlr-layer-shell protocol. It works on Hyprland, labwc, niri, river and Xfce; partly on KDE (use `--app-id=dock`) and Sway; not on GNOME. On X11 it depends on the window manager. Control panels remotely with `kitten @ resize-os-window --action=os-panel`.

## quick-access-terminal: a drop-down terminal

`kitten quick-access-terminal` shows a terminal that slides in from a screen edge; running it again hides it. On Linux, bind the command to a global shortcut in your desktop or window manager.

Settings go in `quick-access-terminal.conf` in the kitty config directory. Defaults: `lines 25`, `columns 80`, `edge top`, `layer overlay`, `background_opacity 0.85`, `hide_on_focus_loss no`, `grab_keyboard no`, `focus_policy exclusive`, `start_as_hidden no`, and `app_id kitty-quick-access`. `kitty_conf` names an extra config file and `kitty_override KEY=VALUE` overrides single options. It is built on the panel kitten, so the same desktop limits apply. To control it remotely:

```
kitty_override allow_remote_control=socket-only
kitty_override listen_on=unix:@quick-term
```

Command-line options: `-c`, `-o`, `--detach`, `--detached-log`, `--instance-group` (default `quick-access`).

## ask: ask the user something from a script

`kitten ask` shows a prompt and returns the answer, for use in mappings and scripts. `--type` is `line` (default), `yesno`, `choices`, `password`, `file` or `calculator`. Other options: `--message`, `--name` (keys the input history), `--choice` (repeatable), `--default`, `--prompt` (default `> `) and `--title`.

## query-terminal: ask the terminal about itself

`kitten query-terminal [QUERY ...]` prints `query: value` lines. A blank value means the terminal does not support that query. Queries: `name`, `version`, `allow_hyperlinks`, `font_family`, `bold_font`, `italic_font`, `bold_italic_font`, `font_size`, `dpi_x`, `dpi_y`, `foreground`, `background`, `background_opacity`, `clipboard_control` and `os_name`. It waits for replies for up to `--wait-for` seconds (default 10).

```
kitten query-terminal version font_family font_size
```

## command-palette: find and run any action

Press `ctrl+shift+f3` to open a searchable list of every action, grouped by category, together with key and mouse bindings. Type to filter by key, action or category; matching ignores case, accepts several words and tolerates small typos once you have typed four characters. `Enter` runs the highlighted action, `Esc` closes. Move with the arrows, `ctrl+k`/`ctrl+p` and `ctrl+j`/`ctrl+n`, or with Page Up/Down, Home and End. `F12` switches whether actions without a key are listed, and that choice is remembered. You can also click entries.

## choose-files: a fuzzy file picker

`kitten choose-files [options] [START_DIR]` lets you find files by typing parts of their names.

- `--mode` is `file` (default), `files`, `dir`, `dirs`, `all`, `save-file`, `save-files` or `save-dir`.
- Other options: `--file-filter`, `--title`, `--display-title`, `--output-format text|json|shell|shell-relative`, `--write-output-to`, `--suggested-save-file-name`, `--clear-cache`, `-o` and `--config`.
- Keys: type to search; `Enter` selects; `Tab` enters a directory; `shift+tab` goes up; `shift+enter` adds to a multiple selection; `ctrl`+click and `alt`+click select several or a range; `ctrl+enter` accepts a directory or lets you type a name to save; `alt+enter` edits an existing name.
- Its own config file can use `map KEY cd PATH` to jump to a directory.

Default shortcuts: `ctrl+shift+p` then `c` inserts a chosen file path at the cursor, and `ctrl+shift+p` then `d` inserts a directory.

## Other kittens

- `edit-in-kitty` and `run-shell` are described in 08-shell-integration.md.
- `dnd` lets you drag files out of the terminal (as `text/uri-list`), even over SSH.
- `desktop-ui` provides desktop pieces such as a portal and colour-scheme reporting for lightweight window managers, with subcommands like `run-server`, `enable-portal` and `set-color-scheme`.
- `mouse-demo` demonstrates mouse reporting.
- `update-self` updates a standalone `kitten` binary.
- `remote_file` is used internally when you click a hyperlink to a file on a host you reached with the ssh kitten; it asks whether to edit or download the file.
- Your own kittens are Python files, run from a mapping such as `map f3 kitten mykitten.py`.

## In Kilix: browse a web page inside a pane

**In Kilix:** the `browse` kitten (run as `kitten browse`) shows a web page inside a kitty pane using Chrome or Chromium, which must be installed as `google-chrome` or `chromium` on your `PATH`. Page images come through kitty's graphics protocol and text is drawn as real terminal characters. Keys include `ctrl+l` for the address bar, `alt+left` and `alt+right` or Backspace for history, `ctrl+r` to reload and `ctrl+c` to copy.


This kitten is not part of upstream kitty.

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
- 10-clipboard-and-links.md
- 12-troubleshooting.md
