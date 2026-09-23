# The launch action and session files in kitty

This guide covers two related features of kitty 0.48.2 as bundled in Kilix on Linux. The `launch` action opens a new kitty window, tab, OS window, overlay or background process running any program, with fine control over its directory, position, title, environment and input. Session files are plain-text descriptions of tabs, windows, layouts and programs that kitty can open at startup, switch between, and save from the current state. The guide explains the main `launch` options, piping screen content into programs, placeholders, watchers, the session-file keywords, and the session actions.

## Where you can use launch

`launch` works in three places:

- In `kitty.conf` as the action of a shortcut: `map f2 launch --type=tab htop`.
- In a session file, as a line starting with `launch`.
- From a script, through remote control: `kitten @ launch ...`.

When you give no command, `launch` starts your default shell. To run several shell commands, wrap them in `sh -c "..."`:

```
map f3 launch --hold sh -c "cd ~/src && git fetch && git status"
```

To reuse a set of `launch` options, give them a name with `action_alias`:

```
action_alias side_tab launch --type=tab --cwd=current
map f4 side_tab
map f5 side_tab btop
```

## Choose what kind of window launch creates

The `--type` option sets what `launch` opens. The default is `window`.

| Value | Result |
|---|---|
| `window` | A new kitty window in the current tab |
| `tab` | A new tab in the current OS window (not allowed in session files) |
| `os-window` | A new OS window (not allowed in session files) |
| `overlay` | A window covering the active kitty window; it is not treated as the active window when kitty works out the current directory or kitten input |
| `overlay-main` | An overlay that is treated as the active window, suited to long-running overlays |
| `background` | A process with no window at all |
| `os-panel` | An OS window used as a desktop panel on Wayland compositors that support layer-shell; configure it with `--os-panel` |
| `clipboard`, `primary` | No window; used with `--stdin-source` to copy data to the clipboard or the primary selection |

A `background` process started with `--allow-remote-control` receives a socket for controlling kitty, announced through `KITTY_LISTEN_ON`.

## Start a new window in the current directory

`--cwd` sets the working directory of the new program. Give a path, or one of these special values:

- `current`: the working directory of the source window (normally the active one).
- `last_reported`: the last directory the shell reported; this needs shell integration.
- `oldest`: the directory of the oldest foreground process in the source window.
- `root`: the directory of the process the source window was originally started with.

```
map ctrl+alt+enter launch --cwd=current
```

If the source window is an ssh kitten session, add `--hold-after-ssh` together with `--cwd=current` so that the new window falls back to a local shell once the remote connection ends.

## Control where the new window appears

`--location` decides where a new kitty window goes in the tab. The default, `default`, lets the layout decide, which usually means after the active window. The other values are `first`, `after`, `before`, `neighbor` (the same as `after`), `last`, and the splits-layout values `vsplit`, `vsplit-before`, `hsplit`, `hsplit-before` and `split`.

- `after` and `before` are relative to the active window. For `--type=tab`, `after` places the new tab immediately beside the current tab rather than as the last tab.
- `vsplit` and `hsplit` only matter in the `splits` layout: the new window appears to the right of, or below, the current one; the `-before` forms place it left or above. `split` chooses by window shape.

`--next-to EXPR` uses a different reference window, chosen by a match expression; for a new tab, the tab opens in that window's OS window. `--bias N` (default 0) sets the new window's share of space; its meaning per layout is described in `05-tabs-windows-layouts.md`.

## Set titles and keep focus

- `--title` (also `--window-title`) sets the new window's title; otherwise the program sets it. `--title current` copies the source window's title.
- `--tab-title` names a new tab; `current` copies the source tab's title.
- `--keep-focus` (also `--dont-take-focus`) leaves focus where it is instead of moving to the new window.
- `--source-window EXPR` picks the window used as the source for copied title, colours, environment, screen content and directory. The active window is the default.

```
map f6 launch --type=tab --tab-title "Logs" --keep-focus journalctl -f
```

## Pass environment variables to a launched program

- `--env NAME=VALUE` sets a variable; repeat it for several. `--env NAME=` sets it empty, and `--env NAME` alone removes it.
- `--copy-env` copies the source window's environment as it was when that window was created. Changes made later inside its shell are not included.
- `--var NAME=VALUE` attaches a user variable to the new window. Match expressions can find the window later as `var:NAME`.

```
map f7 launch --env EDITOR=nvim --var role=scratch
```

## Copy other settings from the source window

- `--copy-colors` gives the new window the same colours as the source window.
- `--copy-cmdline` ignores any command you gave and runs the source window's command line again.
- `--hold` keeps the window open at a shell prompt after the command exits.

## Style a launched window

- `--color KEY=VALUE` changes one colour, or `--color path/to/colors.conf` loads a file of colours. Repeat as needed: `launch --color background=#202020 --color foreground=#e0e0e0`.
- `--spacing` sets margins and padding for this window, for example `--spacing padding=10` or `--spacing margin-h=24`. It is ignored for overlays.
- `--marker SPEC` starts the window with a text marker, in the same syntax as the `toggle_marker` action.
- `--logo PNG` shows an image in the window; `--logo-position` and `--logo-alpha` (default -1, meaning use the configuration value) adjust it.

## Open an OS window with specific properties

When `--type=os-window` is used, these options apply:

- `--os-window-class`: the X11 `WM_CLASS` class or Wayland app ID. By default it is inherited, ultimately `kitty`.
- `--os-window-name`: the X11 `WM_NAME`; defaults to the class.
- `--os-window-title`: a fixed title; `current` copies the source's.
- `--os-window-state`: `normal` (default), `fullscreen`, `maximized` or `minimized`.
- `--os-window-position XxY`: a screen position such as `200x100`. It depends on the window manager and never works on Wayland.

For `--type=os-panel`, `--os-panel KEY=VALUE` (repeatable) passes panel settings, for instance `--os-panel edge=top --os-panel lines=1`.

## Let a launched program control kitty

`--allow-remote-control` lets the program in the new window use remote control even when `allow_remote_control` is off in `kitty.conf`. `--remote-control-password '"secret" action-globs'` (repeatable) restricts it to certain actions with a password; the value `'!'` turns off the global passwords for this window. The password option only works together with `--allow-remote-control`.

## Pipe screen content into a program

`--stdin-source` feeds text from the source window to the new program's standard input. The default is `none`. The sources are:

- `@selection`: the current selection.
- `@screen`, `@screen_scrollback`: the visible screen, optionally with the scrollback.
- `@alternate`, `@alternate_scrollback`: the alternate screen used by full-screen programs.
- `@first_cmd_output_on_screen`, `@last_cmd_output`, `@last_visited_cmd_output`: output of individual commands; these need shell integration.

By default the text is plain. Add `--stdin-add-formatting` to keep colours and styles as escape codes, and `--stdin-add-line-wrap-markers` to insert a carriage return where lines were soft-wrapped.

```
map f9 launch --type=overlay --stdin-source=@last_cmd_output --stdin-add-formatting less -R
```

The program also receives `KITTY_PIPE_DATA` in the form `{scrolled_by}:{cursor_x},{cursor_y}:{lines},{columns}`, with 1-based cursor coordinates. For simpler cases there are dedicated actions: `copy_last_command_output`, `copy_selection_or_last_command_output` and `show_last_command_output`.

## Copy text to the clipboard with launch

Combining `--type=clipboard` (or `--type=primary`) with `--stdin-source` copies the chosen content without opening any window:

```
map f10 launch --type=clipboard --stdin-source=@last_cmd_output
```

## Use placeholders in the launched command

kitty replaces these words in the command's arguments before running it:

| Placeholder | Replaced with |
|---|---|
| `@selection` | The selected text |
| `@active-kitty-window-id` | The ID of the active kitty window |
| `@line-count` | The number of lines sent on standard input (only when there is such input) |
| `@input-line-number` | The input line number |
| `@scrolled-by` | How far the window is scrolled back |
| `@cursor-x`, `@cursor-y` | The cursor position, counting from 1 |
| `@first-line-on-screen`, `@last-line-on-screen` | The first and last lines currently visible |

```
map f11 launch --type=tab man @selection
```

## How launch finds the program to run

If you give a bare program name, kitty looks for it first in its own `PATH`, then in the system's standard directories, and finally in the `PATH` your shell uses. The `exe_search_path` option in `kitty.conf` changes this search.

## React to window events with watchers

A watcher is a Python module whose functions kitty calls when things happen to a window. Attach one to a launched window with `--watcher PATH` (or `-w`, repeatable; relative paths are taken from the configuration directory). For every window, use the `watcher` option in `kitty.conf` instead.

The functions a watcher can define are `on_load`, `on_resize`, `on_focus_change`, `on_close`, `on_set_user_var`, `on_title_change`, `on_cmd_startstop` and `on_color_scheme_preference_change`. Global watchers can also define `on_tab_bar_dirty` and `on_quit`; `on_quit` can cancel quitting.

## Add a launched window to a session

`--add-to-session NAME` makes the new window a member of a session. `.` means the source window's session and `!` means no session. By default, a window launched with a `--cwd` taken from the source window joins the source window's session. This membership is temporary: the session file itself is not changed unless you save it again.

## Write a session file

A session file is a plain-text file with one keyword per line; lines starting with `#` are comments. The usual extension is `.kitty-session`, and `.kitty_session` and `.session` are also recognised when kitty scans a directory. Here is a small session with an editor tab and a monitoring tab:

```
# ~/sessions/project.kitty-session
new_tab code
layout tall
cd ~/work/project
launch nvim
launch --title shell
focus

new_tab monitor
layout grid
launch btop
launch journalctl -f
```

Environment variables such as `$HOME` or `${PROJECT}` are expanded everywhere except in the positional arguments of `launch` (options like `--cwd=$HOME/x` are expanded). A relative `cd` path is resolved against the directory containing the session file.

## Open a session when kitty starts

Start kitty with the session on the command line:

```
kitty --session ~/sessions/project.kitty-session
```

or set it permanently in `kitty.conf` with `startup_session ~/sessions/project.kitty-session`. `--session -` reads the session from standard input, and `kitty --session none` skips the `startup_session` for one start. `kitty --start-as` overrides any window states the session sets.

## Session file keywords for tabs and windows

| Keyword | What it does |
|---|---|
| `new_tab [TITLE]` | Starts a new tab, optionally with a fixed title |
| `layout NAME[:options]` | Sets the current tab's layout |
| `enabled_layouts a,b` | Sets which layouts the current tab may use |
| `cd PATH` | Sets the directory for the following windows in this tab |
| `launch [options] [command]` | Opens a kitty window in the current tab; it cannot create tabs or OS windows |
| `focus` | Focuses the window created by the previous `launch` |
| `focus_matching_window EXPR` | Focuses the window matching an expression, such as `var:role=main` |
| `focus_tab N` or `focus_tab EXPR` | Makes a tab active, by 0-based index or by expression such as `title:monitor` |
| `resize_window ARGS` | Resizes the current window, for example `resize_window taller 3` |
| `title TEXT` | Deprecated; use `launch --title` |

The `set_layout_state` keyword also appears in saved sessions; it is written by `save_as_session` and is not meant to be typed by hand.

## Session file keywords for OS windows

| Keyword | What it does |
|---|---|
| `new_os_window` | Starts a new OS window. Keywords before the first `new_os_window` apply to the first OS window |
| `os_window_title TEXT` | Gives the OS window a fixed title |
| `os_window_class NAME` | Sets the `WM_CLASS` class or Wayland app ID |
| `os_window_name NAME` | Sets the `WM_CLASS` name or Wayland tag |
| `os_window_size W H` | Sets the size in pixels or cells, such as `120c 40c` |
| `os_window_state STATE` | `normal`, `fullscreen`, `maximized` or `minimized` |
| `focus_os_window` | Makes this OS window the focused one (the window manager may refuse) |

## Switch between sessions

`goto_session` switches to a session, starting it if it is not already running. It has no default key, so map it:

```
map ctrl+alt+p goto_session ~/sessions/project.kitty-session
map ctrl+alt+s goto_session
map ctrl+alt+o goto_session ~/sessions
map ctrl+alt+b goto_session -1
```

- With a file path, it opens or switches to that session.
- With no argument, it shows a list of known sessions to choose from.
- With a directory, it lets you pick among the session files in it.
- With `-1`, it returns to the previous session; more negative numbers go further back.

`--sort-by recent` (the default) or `--sort-by alphabetical` orders the list, and `--active-only` limits it to running sessions.

## Close a session

`close_session` closes every window belonging to a session. With no argument it asks which one; `close_session .` closes the active session; and `close_session NAME` or `close_session PATH` closes a specific one.

## Save the current layout as a session

`save_as_session` writes the current OS windows, tabs, windows, programs and directories to a session file. With no path it asks for one; `.` saves over the active session's file. A path you type without an extension gets `.kitty-session` added. Afterwards kitty opens the file in your editor, unless you add `--save-only`.

```
map ctrl+alt+w save_as_session --relocatable ~/sessions/current.kitty-session
```

Options:

- `--save-only`: do not open the saved file in the editor.
- `--relocatable`: store directories relative to the session file's location.
- `--use-foreground-process`: also record the program running in each shell so it restarts when the session loads. This needs shell integration. Be careful, since it would re-run commands that change or delete things.
- `--match EXPR`: save only matching windows; `--match=session:.` saves just the active session.
- `--base-dir DIR`: where to save relative file names.

Connections made with the ssh kitten are recorded too, including the remote directory and running program.

## Keep new windows in the active session

Newly opened windows join the active session only when opened with `new_window_with_cwd`, `new_tab_with_cwd`, `new_os_window_with_cwd` or `launch --add-to-session`. This membership is temporary until you save the session again.

To show only the current session's tabs in the tab bar, set `tab_bar_filter session:~ or session:^$` in `kitty.conf`. To show the session name in tab titles, use `{session_name}` or `{active_session_name}` in `tab_title_template`.

## See also

- `01-getting-started.md` - kitty's building blocks and first steps
- `02-command-line.md` - starting kitty and its command-line options
- `03-configuration.md` - the `kitty.conf` file and its options
- `04-keyboard-and-mouse.md` - shortcuts and mouse bindings
- `05-tabs-windows-layouts.md` - managing tabs, windows and layouts
