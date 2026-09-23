# Getting started with kitty

kitty is a terminal emulator that draws its whole interface on the graphics card. This guide covers kitty 0.48.2, the version bundled inside the Kilix terminal on Linux. It explains how kitty organises your work into OS windows, tabs, windows and layouts, which key presses you need on your first day, where the configuration file lives, how to reload it after editing, and where to look when you need more help. Every shortcut below assumes the Linux defaults, where the special modifier `kitty_mod` stands for `ctrl+shift`.

## What kitty is

kitty is a terminal emulator that renders all of its text and decorations with OpenGL instead of relying on a large desktop toolkit. The performance-critical parts are written in C, the user interface and extension points in Python, and most of the helper command-line programs (called kittens) in Go.

kitty is designed to be driven from the keyboard: every feature can be reached without a mouse, although mouse support is complete as well. kitty handles full Unicode, 24-bit "true color", bold and italic text, and underlines that can be coloured and styled, including curly underlines used by spell checkers and linters.

All of kitty's settings live in a single plain-text file called `kitty.conf`. There is no settings dialog; you edit that file and kitty picks up the changes.

## Understand OS windows, tabs and windows

kitty uses a three-level hierarchy, and the names matter because the shortcuts and settings refer to them.

- **OS window**: a top-level window that your desktop environment or compositor manages, with its own place on the taskbar.
- **Tab**: a group of terminals inside an OS window. Every OS window holds at least one tab.
- **Window** (sometimes "kitty window"): a single terminal pane inside a tab. Every tab holds at least one kitty window.

So one OS window can contain several tabs, and each tab can show several kitty windows side by side. When kitty documentation says "window" on its own, it means a kitty window (a pane), not the OS window.

## Understand layouts

A layout is the rule a tab uses to arrange its kitty windows automatically, much like a tiling window manager. You never drag panes into place by hand; you pick a layout and kitty tiles the windows for you. Each tab has its own layout, so one tab can use a side-by-side arrangement while another shows a single full-size window.

kitty ships seven layouts: `fat`, `grid`, `horizontal`, `splits`, `stack`, `tall` and `vertical`. Press `ctrl+shift+l` (the `next_layout` action) to cycle through the layouts that are enabled. See `05-tabs-windows-layouts.md` for a description of each layout.

## Understand overlay windows and kittens

An overlay window is a kitty window that sits on top of another kitty window and covers it completely. kitty uses overlays for temporary tools such as the scrollback pager, the hints picker and the Unicode character input. A plain overlay is not counted as the active window when kitty works out the current directory or which window a kitten should read from. A variant called `overlay-main` is treated as the active window, which suits long-running overlays.

Kittens are small helper programs that extend kitty. You run them as `kitten <name>`, for example `kitten themes`. Most built-in kittens are written in Go and a few in Python; you can also write your own kittens in Python.

## Open your first windows and tabs

These default Linux shortcuts cover the basics of working in kitty:

| What you want | Keys |
|---|---|
| Open a new kitty window (pane) in the current tab | `ctrl+shift+enter` |
| Open a new tab | `ctrl+shift+t` |
| Open a new OS window | `ctrl+shift+n` |
| Switch to the next layout | `ctrl+shift+l` |
| Copy the selection to the clipboard | `ctrl+shift+c` |
| Paste from the clipboard | `ctrl+shift+v` |
| Page through the scrollback | `ctrl+shift+h` |

A new kitty window is placed by the current layout, so pressing `ctrl+shift+enter` a few times and then `ctrl+shift+l` is a quick way to see how each layout arranges the panes. The complete shortcut list is in `04-keyboard-and-mouse.md`.

## Find the command palette

The command palette lists every kitty action together with the key currently bound to it, and lets you run any of them. Open it with `ctrl+shift+f3`. The palette is the fastest way to discover an action whose name you do not remember, or to check which shortcut runs it.

## Select and copy text with the mouse

kitty's mouse selection follows familiar conventions:

- Drag with the left button to select text.
- Double-click selects a word; triple-click selects a whole line. Keep dragging after the double- or triple-click to extend by words or lines.
- Right-click extends the existing selection to the click point.
- `ctrl+alt` plus drag makes a rectangular (column) selection.
- `ctrl+alt` plus triple-click selects everything from where you clicked through to the line's end.
- Selected text goes to the primary selection where the system supports one, and middle-click pastes it.

When a program such as a text editor has taken over the mouse, hold `shift` while clicking or dragging to make kitty select text anyway.

## Open links and command output with the mouse

A plain left click on a URL opens it, as long as the program in the window has not grabbed the mouse. With shell integration active, `ctrl+shift` plus right-click on a command's output opens that output in the pager.

The tab bar also responds to the mouse. Drag a tab to reorder it, drop it onto another OS window to move it there, or drop it outside any window to give it its own OS window. Double-click an empty part of the tab bar to open a new tab, and double-click a tab to rename it. To resize kitty windows, drag the borders between them.

## Find your configuration file

On Linux, kitty's configuration file is normally `~/.config/kitty/kitty.conf`. kitty decides which configuration directory to use like this:

1. If the environment variable `KITTY_CONFIG_DIRECTORY` is set, that directory is always used.
2. Otherwise `$XDG_CONFIG_HOME/kitty`, then `~/.config/kitty`, then the `kitty` subdirectory of each entry in `$XDG_CONFIG_DIRS`, taking the first that exists.
3. If none exists, kitty creates `$XDG_CONFIG_HOME/kitty` (or `~/.config/kitty`).

A system-wide file at `/etc/xdg/kitty/kitty.conf`, if present, is read first, so anything in your own `kitty.conf` takes precedence over it.

## Edit the configuration file

Press `ctrl+shift+f2` (the `edit_config_file` action) to open `kitty.conf` in a text editor. If the file does not exist yet, kitty creates one for you that contains every option, commented out, with a description of each. That makes a good starting point: uncomment a line and change its value.

The editor is chosen by the `editor` option. Its default value `.` means kitty tries `$VISUAL`, then `$EDITOR`, then looks for an editor set in your shell's startup files, and finally falls back to the first well-known editor it can find.

To print the complete commented default configuration to your terminal instead, run:

```
kitty +runpy 'from kitty.config import *; print(commented_out_default_config())'
```

## Reload the configuration after editing

kitty watches `kitty.conf` and reloads it automatically shortly after you save it. The `auto_reload_config` option sets the delay (0.1 seconds by default); a negative value turns automatic reloading off. Automatic reloading only works when `kitty.conf` already existed when kitty started.

To reload by hand, press `ctrl+shift+f5` (the `load_config_file` action), or send the `SIGUSR1` signal to the kitty process. From a shell running inside kitty, the `KITTY_PID` variable holds that process ID:

```
kill -SIGUSR1 $KITTY_PID
```

A handful of options only take effect after a restart; `03-configuration.md` lists them.

## Check which settings are active

Press `ctrl+shift+f6` (the `debug_config` action) to see the configuration kitty is actually using, including your shortcuts. This is the right tool when a setting seems to be ignored. There is no `--debug-config` command-line flag in kitty 0.48.2; use the key or the `debug_config` action instead.

## Get help inside kitty

Several help sources are built in:

- `ctrl+shift+f1` opens kitty's local documentation (the `show_kitty_doc` action). You can map it to a specific page, for example `show_kitty_doc conf` for the configuration reference.
- `ctrl+shift+f3` opens the command palette of actions and shortcuts.
- `kitty --version` prints the version, which for Kilix is `kitty 0.48.2`.
- `kitty --help` summarises the command-line options.
- `kitten --help` lists the available kittens, and `kitten <name> -h` shows help for one kitten.
- `kitten @ --help` lists the remote-control commands.

## Find out what a key sends

When a shortcut does not behave as expected, two tools show what is happening:

- `kitten show-key` prints the bytes each key press sends to programs using the traditional encoding. Add `-m kitty` to see the same key in kitty's own keyboard protocol.
- `kitty --debug-input` starts kitty with logging of every key and mouse event, including how kitty handled it.

## Explore the built-in kittens

kitty 0.48.2 in Kilix includes these kittens: `@` (remote control), `update-self`, `edit-in-kitty`, `clipboard`, `dnd`, `icat`, `browse`, `ssh`, `transfer`, `panel`, `quick-access-terminal`, `unicode-input`, `show-key`, `desktop-ui`, `mouse-demo`, `hyperlinked-grep`, `ask`, `hints`, `diff`, `notify`, `themes`, `run-shell`, `choose-fonts`, `choose-files`, `command-palette` and `query-terminal`. A good first one to try is `kitten themes`, which lets you preview and pick a colour theme.

## Learn about other kitty features

A few more features are worth knowing about early:

- **Remote control** lets scripts and shells drive kitty with `kitten @ <command>`. It is off by default (`allow_remote_control no`).
- **Sessions** are text files describing tabs, windows, layouts and programs to open; start one with `kitty --session FILE` or the `startup_session` option. See `06-launch-and-sessions.md`.
- **Shell integration** for bash, zsh and fish is on by default (`shell_integration enabled`) and powers features such as jumping between prompts and viewing the last command's output.
- **Marks** highlight text on screen that matches a regular expression.
- **Named copy buffers**: `copy_to_buffer NAME` and `paste_from_buffer NAME` give you extra clipboards. They have no default keys.
- **Watchers** are Python callbacks that run on window events such as resizing, closing, focus or title changes.
- **Scrollbar**: kitty draws a scrollbar at the right edge, shown while you scroll by default (`scrollbar scrolled`), which you can click and drag.

For developers, kitty also defines a graphics protocol for showing images, a keyboard protocol that reports keys unambiguously, and a text-sizing protocol for text that spans several cells.

## In Kilix: extra options and actions

Kilix adds a few things that are not part of upstream kitty:

- The option `software_mouse_cursor` (default `block`, other values `pointer` and `none`) makes Kilix draw the mouse pointer inside the terminal grid and hide the system pointer over the grid. Set it to `none` to keep the normal system pointer.
- Kilix defines the actions `kilix_show_start_menu`, `kilix_windows_key`, `kilix_toggle_synchronized_input`, `kilix_close_persistent_window` and `kilix_show_memory_widget`. They have no default Linux keys in kitty's own configuration, so bind them with `map` if you want them on a key.

In Kilix, the `kilix` launcher sets `KITTY_CONFIG_DIRECTORY` to Kilix's own configuration directory: the directory named by `KILIX_CONFIG_DIRECTORY` if that is set, otherwise Kilix's per-user configuration directory. Rule 1 above therefore applies, and `~/.config/kitty` is not read; a separately installed kitty keeps using it. The Kilix README describes that directory's files.

## See also

- `02-command-line.md` - starting kitty and its command-line options
- `03-configuration.md` - the `kitty.conf` file and its options
- `04-keyboard-and-mouse.md` - shortcuts and mouse bindings
- `05-tabs-windows-layouts.md` - managing tabs, windows and layouts
- `06-launch-and-sessions.md` - the `launch` action and session files
