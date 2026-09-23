# Remote control: scripting kitty with `kitten @`

kitty can be driven from the outside. A program or script can ask a running kitty to open windows and tabs, send keystrokes, read what is on screen, change colors and fonts, rename things, and much more. All of this goes through the `kitten @` command (the "remote control" client). Remote control is switched off by default, so this page starts with how to turn it on safely, then covers sockets and passwords, the full list of `kitten @` subcommands with their most useful flags, the matching language used to pick windows and tabs, the JSON produced by `kitten @ ls`, and the environment variables kitty gives to programs. It ends with worked examples of everyday tasks.

## Turn remote control on

Remote control is governed by the `allow_remote_control` option in `kitty.conf`. Its default is `no`, which means every remote control request is refused.

The accepted values are:

| Value | Requests over the terminal (TTY) | Requests over a socket |
|---|---|---|
| `no` (also `n`, `false`) | refused | refused |
| `yes` (also `y`, `true`) | accepted | accepted |
| `socket` | checked against passwords | accepted |
| `socket-only` | refused | accepted |
| `password` | checked against passwords | checked against passwords |

A "TTY request" is one a program sends by writing escape codes into the kitty window it runs in. Such requests can come from any program in the window, including programs on a remote machine you reached with SSH. That is why `yes` is the least safe choice: anything that can print to your terminal can control kitty.

For most people, `socket-only` is a good balance. Local scripts talk to kitty through a socket, and nothing printed into a window can take control.

```
allow_remote_control socket-only
listen_on unix:@kitty-ctl
```

A change to `allow_remote_control` or `listen_on` should be followed by a full restart of kitty, because `listen_on` is not re-read when the configuration is reloaded.

## Choose a socket address with `listen_on`

The `listen_on` option tells kitty where to listen for remote control connections. Its default is `none` (no socket). kitty only honours `listen_on` when `allow_remote_control` is `yes`, `socket` or `socket-only`.

Address forms:

- `unix:/path/to/socket` - a Unix socket file. A relative path is placed in the temporary directory, and any `$VARIABLE` written in the path is replaced by its value.
- `unix:@name` - a Linux abstract socket (no file on disk).
- `tcp:localhost:12345` - a TCP socket. When set through `listen_on`, kitty always picks a random port, even if you write a non-zero one.

kitty makes the address unique per process. If the value contains `{kitty_pid}`, that text is replaced with kitty's process ID. If it does not, kitty appends `-<pid>` to the address. So `unix:@kitty-ctl` actually becomes something like `unix:@kitty-ctl-41234`. Scripts running inside kitty do not need to know this; they find the real address in `KITTY_LISTEN_ON` (see below).

## Enable remote control for one launch only

You can turn remote control on from the command line without touching `kitty.conf`. The `--listen-on` flag overrides `listen_on` and accepts the same address forms:

```
kitty -o allow_remote_control=socket-only --listen-on unix:@my-kitty
```

To start kitty with no visible window, for example to have a script build a layout first, add `--start-as=hidden`.

## Give remote control to a single window

Sometimes you want one trusted helper to control kitty while everything else stays locked out. The `launch` action can grant remote control to just the window it creates, even when `allow_remote_control` is `no`:

```
map f12 launch --allow-remote-control ~/bin/arrange-my-windows
```

Only programs running in that new window can send commands. You can narrow this further with `--remote-control-password`, which takes a password followed by the commands it permits:

```
map f12 launch --allow-remote-control --remote-control-password '"s3cret" ls focus-window' ~/bin/picker
```

Passing `'!'` as the value disables the global passwords for that window.

## What never needs `allow_remote_control`

Three ways of issuing commands work even with `allow_remote_control no`:

- a key mapping using the `remote_control` action,
- a key mapping using the `remote_control_script` action,
- the interactive kitty shell opened with the `kitty_shell` action (default `ctrl+shift+escape`).

These are safe because they can only be triggered by you pressing keys.

## Protect remote control with passwords

The `remote_control_password` option (available since kitty 0.26.0) lets you define passwords and limit what each password may do. It can appear many times:

```
remote_control_password "layout-pw" goto-layout last-used-layout
remote_control_password "colors-pw" set-colors get-colors *-colors
remote_control_password "admin-pw"
remote_control_password "" ls
```

How the lines are read:

- After the password, list the `kitten @` subcommand names it allows. Glob patterns such as `set-tab-*` or `*-colors` work.
- A password with no commands after it may run every command.
- The empty password `""` sets which commands are allowed when a client sends no password at all.
- The last word may instead be a path to a Python file (relative paths are resolved against the kitty config directory). That file defines `is_cmd_allowed(pcmd, window, from_socket, extra_data)`. It should return `True` to allow, `False` to deny, or `None` to have no opinion. Inside it, `pcmd['cmd']` is the command name and `pcmd['payload']` holds the arguments. Anything it prints goes to kitty's standard output.

Use passwords together with `allow_remote_control password`, or with `socket` if you only want TTY requests checked.

If a client sends a password kitty does not recognise, kitty asks you whether to allow or deny that request, or every request carrying that password. Your answer lasts until that kitty process exits.

## Send a password from the client

`kitten @` has four global options for passwords:

- `--password=PW` gives the password directly.
- `--password-file=FILE` reads it from a file. The default file is `rc-pass` in the kitty config directory. Use `-` for standard input or `fd:N` for an open file descriptor.
- `--password-env=NAME` reads it from an environment variable. The default variable is `KITTY_RC_PASSWORD`.
- `--use-password` is `if-available` (the default), `always` or `never`.

Password-protected commands sent from a remote host over SSH are encrypted, which makes large payloads such as background images slower. The remote host needs `KITTY_PUBLIC_KEY` set (the ssh kitten forwards it for you), and the clocks on both machines must agree to within a few minutes, because the encryption uses a time-based nonce.

## Run `kitten @` commands

The general shape is:

```
kitten @ [global options] SUBCOMMAND [options] [arguments]
```

Useful facts about the client:

- Running `kitten @` with no subcommand opens an interactive kitty shell with tab completion.
- `kitten @ SUBCOMMAND -h` shows help for one subcommand.
- Inside a kitty window you usually need no address at all. The client talks over the terminal, or uses `KITTY_LISTEN_ON`. This also works from inside an SSH session running in a kitty window.
- From outside kitty, name the target with `--to ADDRESS`, for example `kitten @ --to unix:@kitty-ctl-41234 ls`. Without `--to`, the client tries `$KITTY_LISTEN_ON` and then the controlling terminal.
- `kitten` is a single static binary, so you can copy it to another Unix machine and use it there as a remote control client.

If all you want is many OS windows sharing one kitty process, `kitty --single-instance` may be simpler than remote control.

## Bind remote control commands to keys

The `remote_control` action runs a `kitten @` subcommand from a key mapping. Everything after the action name is written exactly as you would type it after `kitten @`:

```
map f7 remote_control set-font-size 16
map f8 remote_control set-spacing padding=0
```

Put `!` before the subcommand name to ignore errors, which is handy when a match might find nothing:

```
map f1 remote_control !focus-window --match title:^notes
```

For anything longer, use `remote_control_script`. It runs a script that may call `kitten @` freely. Relative paths resolve against the kitty config directory. It behaves much like `launch --type=background --allow-remote-control`:

```
map f6 remote_control_script tidy-tabs.sh
```

## Flags shared by many subcommands

Many subcommands accept the same targeting and behaviour flags:

- `--match` / `-m` picks windows using the match language described below.
- `--match-tab` / `-t` picks tabs.
- `--self` acts on the window or tab the command runs in, rather than the active one.
- `--all` / `-a` acts on everything.
- `--no-response` returns immediately without waiting; any failure goes unreported.

## Subcommands for windows and tabs

- `launch [CMD ...]` starts a program in a new window, tab, OS window, overlay and so on. It prints the new window's id unless `--no-response` is used. Its flags are listed in the next section.
- `new-window` is deprecated; use `launch` instead.
- `close-window` and `close-tab` close what `-m` (or `--self`) selects. `--ignore-no-match` suppresses the error when nothing matches.
- `focus-window` focuses a window (by default the one running the command). `focus-tab` focuses a tab and its active window.
- `detach-window` moves a window. `--target-tab new` puts it in a new tab; with no target it goes to a new OS window. `--stay-in-tab` keeps focus where it was.
- `detach-tab` moves a tab to a new or different OS window with `--target-tab`.
- `select-window` lets the user pick a window visually and prints the chosen id. Flags: `--title`, `--exclude-active`, `--reactivate-prev-tab`, and `--response-timeout` (default 60 seconds).
- `set-tab-title [TITLE]` renames a tab. With no title, the tab goes back to showing its active window's title.
- `set-window-title [TITLE]` renames a window. With no title, the program's last title comes back. `--temporary` lets the program change it again later.
- `set-tab-color` sets tab bar colors using keys `active_fg`, `active_bg`, `inactive_fg`, `inactive_bg`. Values are color names, `#rrggbb` or `NONE`.
- `resize-window` resizes within the layout. `--increment` / `-i` defaults to 2 (negative shrinks); `--axis` is `horizontal`, `vertical` or `reset`.
- `resize-os-window` changes the OS window itself. `--action` is `resize`, `hide`, `show`, `toggle-fullscreen`, `toggle-maximized`, `toggle-visibility` or `os-panel`; size with `--width`, `--height`, `--unit cells|pixels` and `--incremental`.
- `goto-layout NAME` switches layout (use `-m all` for every tab). `last-used-layout` switches back. `set-enabled-layouts` changes the list of layouts a tab may cycle through.

## Launch flags worth knowing

The `launch` subcommand accepts the same options as the `launch` action (see 06-launch-and-sessions.md). The most useful:

- `--type`: `window` (default), `tab`, `os-window`, `overlay`, `overlay-main`, `background`, `clipboard`, `primary`, `os-panel`.
- `--cwd`: a path, or `current`, `last_reported` (needs shell integration), `oldest`, `root`.
- `--title` (alias `--window-title`), `--tab-title`, `--keep-focus` (alias `--dont-take-focus`).
- `--location`: `default`, `after`, `before`, `first`, `last`, `neighbor`, `split`, `hsplit`, `hsplit-before`, `vsplit`, `vsplit-before`; plus `--next-to MATCH` and `--bias`.
- `--env NAME=VALUE` (repeatable), `--var NAME=VALUE` (a user variable), `--copy-env`, `--copy-cmdline`, `--copy-colors`.
- `--hold` keeps the window open after the program exits.
- `--stdin-source` feeds text into the program: `@screen`, `@screen_scrollback`, `@selection`, `@alternate`, `@alternate_scrollback`, `@first_cmd_output_on_screen`, `@last_cmd_output`, `@last_visited_cmd_output`, or `none`.
- `--os-window-title`, `--os-window-class`, `--os-window-name`, `--os-window-state normal|fullscreen|maximized|minimized`.
- `--wait-for-child-to-exit`, and `--response-timeout` (default 86400 seconds).

## Subcommands for text, keys and screen content

- `send-text TEXT` types text into a window (the active one by default). The text understands Python-style escapes such as `\e` for Escape and `\r` for Return. `--stdin` and `--from-file` read text instead; that text is sent as-is without escape processing. `--bracketed-paste` is `disable` (default), `auto` or `enable`. Targets: `-m`, `-t`, `--all`, `--exclude-active`.
- `send-key KEYS...` sends key presses such as `ctrl+a` or `enter`, with the same targeting flags.
- `get-text` prints a window's text. Flags: `--extent`, `--ansi` (keep colors and styles), `--add-cursor`, `--add-wrap-markers`, `--clear-selection`, `--self`, `-m`.
- `scroll-window AMOUNT` scrolls a window. AMOUNT is `start`, `end`, or a number with an optional unit: `l` lines (default), `p` pages, `u` unscroll, `r` prompts. A trailing `-` scrolls up. Fractions work, so `0.5p` is half a page and `1r-` goes to the previous prompt.
- `signal-child [SIGNAL ...]` signals the foreground process (SIGINT by default).
- `create-marker` and `remove-marker` add or remove highlighting (see 09-scrollback-search-marks.md).

Note that `send-text` and `send-key` always report success, even when the match found no window.

## What `get-text --extent` can capture

| Extent | What you get |
|---|---|
| `screen` (default) | the visible screen |
| `all` | the screen plus scrollback |
| `selection` | the current selection |
| `first_cmd_output_on_screen` | output of the first command visible on screen |
| `last_cmd_output` | output of the most recent command |
| `last_non_empty_output` | the most recent command output that was not empty |
| `last_visited_cmd_output` | the output below the prompt you last jumped to |
| `alternate` | the other screen buffer (the one not showing) |
| `alternate_scrollback` | the alternate buffer plus its scrollback |

The four command-output extents rely on shell integration (see 08-shell-integration.md).

## Subcommands for appearance and configuration

- `set-colors` takes `name=value` pairs or a color config file. `--reset` restores the original colors; `--configured` also changes what later windows get. `get-colors` prints colors in `kitty.conf` form (`--configured` shows configured rather than current values).
- `set-font-size SIZE` sets the size in points for an OS window. `0` resets. A prefix of `+`, `-`, `*` or `/` changes it relatively. Put `--` before a negative value. `--all` also applies to OS windows opened later.
- `set-background-opacity` needs `dynamic_background_opacity yes`. It supports `--all`, `--toggle`, `-m`, `-t` and applies per OS window.
- `set-background-image PATH|none|INDEX` accepts PNG, JPEG, WEBP, GIF, BMP and TIFF. `--layout` is one of `configured`, `centered`, `clamped`, `cscaled`, `mirror-tiled`, `scaled`, `tiled`. Index steps like `+1` or `-1` also work (use `--` before `-1`).
- `set-spacing` changes padding and margin, for example `margin=20`, `padding-left=10`, `margin-h=30`; `default` restores a value.
- `set-window-logo PATH|none` shows a logo in a window, with `--position` and `--alpha`.
- `disable-ligatures` takes `never`, `always` or `cursor`.
- `load-config [FILE ...]` reloads configuration. With no file it reloads what was loaded before. `--override name=value` adds overrides; `--ignore-overrides` drops earlier ones. File paths refer to the machine kitty runs on.

## Other subcommands

- `action ACTION [ARGS]` runs any mappable action, with arguments written as in `kitty.conf`.
- `kitten NAME` runs a built-in kitten or your own `.py` kitten in the selected window. Relative paths resolve against the config directory.
- `env VAR=value ...` changes the environment for programs started from now on; a bare `VAR` removes it.
- `set-user-vars NAME=VALUE ...` sets per-window user variables. A bare `NAME` removes one; no arguments prints them.
- `run CMD ...` runs a program on the machine where kitty runs and returns its output and exit code. It accepts `--env`, `--allow-remote-control` and `--remote-control-password`.
- `ls` lists everything as JSON (see below).

## Pick windows with `--match`

A match expression has the form `field:query`. For numeric fields the query is a number; for the rest it is a regular expression. Combine terms with `and`, `or`, `not` and parentheses, and put quotes around queries containing spaces, like `title:"build log"`. The special value `all` matches every window.

Window fields:

- `id` - window id. Negative ids count back from the newest, so `id:-1` is the most recently created window.
- `title`, `cwd`, `cmdline` - regular expressions.
- `pid` - process id.
- `num` - position in the current tab, counting from 0 clockwise, in the same order `ls` uses.
- `recent` - `0` is the active window of the current tab, `1` the one before it, and so on.
- `env` - `env:NAME` or `env:NAME=VALUE`.
- `var` - a user variable, `var:NAME` or `var:NAME=VALUE`.
- `state` - `active` (active in its tab), `focused` (receiving keyboard input, or the last one that did), `needs_attention`, `parent_active`, `parent_focused`, `focused_os_window`, `self` (the window running the command), `overlay_parent` (the window under an overlay).
- `neighbor` - `left`, `right`, `top` or `bottom` of the active window.
- `session` - session name. `^$` means "not from a session", `.` the current session, `~` the current or last active session.

Examples: `cwd:projects and not state:focused`, or `(title:htop or cmdline:btop) and env:WORKSPACE`.

## Pick tabs with `--match-tab`

Tab matching uses the same syntax with these fields: `id`, `index`, `title`, `window_id`, `window_title`, `pid`, `cwd`, `cmdline`, `env`, `var`, `state`, `session`, `recent`.

- `index` counts tabs in the active OS window.
- `recent:0` is the active tab and `recent:1` the previous one.
- If `title` or `id` finds no tab, kitty tries matching a window and uses that window's tab.
- `env` and `var` match any tab that contains such a window.
- Tab states are `active`, `focused`, `needs_attention`, `parent_active`, `parent_focused`, `focused_os_window`.

## List windows as JSON with `kitten @ ls`

`kitten @ ls` prints an array of OS windows. It accepts `-m`, `-t` and `--self` to limit the output.

- Each OS window has `id`, `platform_window_id`, `is_active`, `is_focused`, `last_focused`, `wm_class`, `wm_name`, `background_opacity`, `active_tab_history` and `tabs`.
- Each tab has `id`, `title`, `title_overridden`, `is_active`, `is_focused`, `layout`, `layout_state`, `layout_opts`, `enabled_layouts`, `groups`, `active_window_history` and `windows`.
- Each window has `id`, `title`, `title_overridden`, `is_active`, `is_focused`, `is_self`, `pid`, `cwd`, `cmdline`, `last_reported_cmdline`, `last_cmd_exit_status`, `at_prompt`, `foreground_processes`, `env`, `user_vars`, `lines`, `columns`, `created_at`, `last_focused_at`, `in_alternate_screen`, `neighbors`, `session_name`, `needs_attention` and `has_activity_since_last_focus`.

The `env` field only shows variables that differ from kitty's own environment; add `--all-env-vars` to see all of them. With `--output-format session`, `ls` prints a kitty session file instead of JSON.

A quick way to list every window's id and title with `jq`:

```
kitten @ ls | jq -r '.[].tabs[].windows[] | "\(.id)\t\(.title)"'
```

## Environment variables kitty sets for programs

Programs started inside kitty receive:

- `KITTY_WINDOW_ID` - the id of the window they run in. Use it as `--match id:$KITTY_WINDOW_ID`.
- `KITTY_LISTEN_ON` - the remote control address, when kitty is listening. Windows started with `launch --allow-remote-control` get an `fd:N` value instead. `kitten @` uses this when `--to` is absent.
- `KITTY_PID` - kitty's process id.
- `KITTY_PUBLIC_KEY` - the key used for encrypted password requests.
- `KITTY_INSTALLATION_DIR` - where kitty is installed.
- `TERM` - from the `term` option, `xterm-kitty` by default - and `COLORTERM=truecolor`.

On the client side, `KITTY_RC_PASSWORD` is the default variable read for a password.

**In Kilix:** programs also see `KITTY_KILIX_RENDERING=1`, and `KITTY_PTY_BROKER_SESSION` when a PTY broker session exists. These are Kilix additions and do not exist in upstream kitty.

## Example: find a window by title and read its text

Say a server log is running in a window titled "api-server" and you want its last lines from another window:

```
kitten @ get-text --match 'title:^api-server' --extent all | tail -n 20
```

To keep colors, add `--ansi`. To get only the output of the last command run there (with shell integration active), use `--extent last_cmd_output`.

## Example: send text and a key to another window

Run the tests in the window whose working directory ends in `myapp`, without leaving your editor:

```
kitten @ send-text --match 'cwd:myapp$' 'pytest -q'
kitten @ send-key --match 'cwd:myapp$' enter
```

The same thing in one step, using an escape for Return:

```
kitten @ send-text --match 'cwd:myapp$' 'pytest -q\r'
```

To interrupt whatever is running there instead: `kitten @ send-key --match 'cwd:myapp$' ctrl+c`.

## Example: open a new tab in a given directory

```
kitten @ launch --type=tab --cwd ~/src/website --tab-title website
```

The command prints the new window's id, which you can store and reuse:

```
id=$(kitten @ launch --type=tab --cwd ~/src/website --keep-focus)
kitten @ send-text --match "id:$id" 'npm run dev\r'
```

## Example: rename a tab

Rename the tab you are in:

```
kitten @ set-tab-title "deploy"
```

Rename a different tab, found by the title of one of its windows:

```
kitten @ set-tab-title --match 'title:vim' "editing"
```

Clear the custom name so the tab follows its window's title again: `kitten @ set-tab-title`.

## Example: control kitty from a script outside it

```
kitty -o allow_remote_control=socket-only --listen-on 'unix:/tmp/kt-{kitty_pid}' &
# later, with the real path:
kitten @ --to unix:/tmp/kt-12345 ls
```

Using `{kitty_pid}` puts the process id exactly where you want it in the path, instead of having it appended.

## See also

- 01-getting-started.md
- 02-command-line.md
- 03-configuration.md
- 04-keyboard-and-mouse.md
- 05-tabs-windows-layouts.md
- 06-launch-and-sessions.md
- 08-shell-integration.md
- 09-scrollback-search-marks.md
- 10-clipboard-and-links.md
- 11-kittens.md
- 12-troubleshooting.md
