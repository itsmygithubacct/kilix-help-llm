# Starting kitty from the command line

This guide explains how to start kitty 0.48.2 (as bundled in Kilix on Linux) from a shell or launcher, and which command-line options are worth knowing. It covers running a specific program instead of your shell, choosing configuration files and overriding single settings, opening a session, reusing an already running kitty, setting window class and title for your window manager, the debugging switches, the `+` and `@` subcommands of the `kitty` binary, and the environment variables kitty reads or sets.

## Understand the basic command form

The general shape of a kitty command line is:

```
kitty [options] [program-to-run ...]
```

With no arguments, kitty opens one OS window running your login shell. Anything you put after the options is treated as a program to run in the first window instead of the shell. For example, to open kitty straight into `htop`:

```
kitty htop
```

When that program exits, its window closes. Add `--hold` to keep the window open afterwards (see below).

## Run a command and keep the window open

The `--hold` option keeps the first window open after its program finishes, and leaves you at a shell prompt there. This is handy for commands that print something and exit, so you can read the result:

```
kitty --hold sh -c "df -h; free -m"
```

Wrapping several commands in `sh -c "..."` is the usual way to run more than one command as the window's program.

## Start in a particular directory

Use `-d` (long forms `--working-directory` or `--directory`) to choose the directory kitty's first window starts in. The default is `.`, the directory you launched kitty from.

```
kitty -d ~/projects/website
```

## Choose which configuration file to load

By default kitty reads `kitty.conf` from its configuration directory. The `-c` option (long form `--config`) names a configuration file explicitly:

```
kitty -c ~/configs/presentation.conf
```

Details of `-c`:

- You can repeat `-c`. The files are merged in the order given, each on top of kitty's built-in defaults and the previous files.
- `-c NONE` loads no configuration file at all, which is useful for testing whether a problem comes from your settings.
- `-c -` or `-c /dev/stdin` reads the configuration from standard input.

When `-c` is not given, kitty looks for `kitty.conf` in `$XDG_CONFIG_HOME/kitty/`, then `~/.config/kitty/`, then the `kitty` directory under each entry of `$XDG_CONFIG_DIRS`, and uses the first one that exists. If `KITTY_CONFIG_DIRECTORY` is set, kitty uses that directory and does not search. In every case `/etc/xdg/kitty/kitty.conf`, if it exists, is loaded first with lower priority.

## Override a single setting for one run

The `-o` option (long form `--override`) sets one configuration option for this kitty instance only, without touching your `kitty.conf`. Write it as `name=value`; `name value` is accepted too. Repeat `-o` for several settings:

```
kitty -o font_size=16 -o background=#1e1e2e
```

`-o` also works for shortcut lines, so you can add a mapping for one run:

```
kitty -o 'map f5 new_tab'
```

## Open a session file at startup

The `--session` option opens a session file, which describes the tabs, windows, layouts and programs to create. Session files are covered in `06-launch-and-sessions.md`.

```
kitty --session ~/sessions/dev.kitty-session
```

Points to know about `--session`:

- `--session -` reads the session from standard input.
- `--session none` ignores any `startup_session` set in `kitty.conf`, so kitty starts plainly.
- Environment variables in the path are expanded, and a relative path is looked up in the configuration directory.
- When a session is given, any program named at the end of the command line is ignored.

## Start fullscreen, maximized or hidden

The `--start-as` option chooses how the OS windows first appear. The choices are `normal` (the default), `fullscreen`, `maximized`, `minimized` and `hidden`.

```
kitty --start-as maximized
```

The chosen state applies to every OS window that a session creates, and it overrides any window states written in the session file. `hidden` starts kitty with no visible window, which is useful for running kitty as a background server.

## Place the first window on screen

`--position` asks for a screen position for the first OS window, written as `XxY`, for example `--position 100x50`. Whether it is honoured depends on your window manager, and it never works on Wayland.

## Reuse one kitty process for many windows

With `-1` (long form `--single-instance`), kitty first checks whether a kitty started the same way is already running. If so, the new command simply asks that kitty to open a new OS window and then exits. New windows start faster this way and share the running instance's cached glyphs on the GPU.

```
kitty -1
```

Related options:

- `--instance-group NAME` keeps separate groups of single-instance kittys apart. Two `kitty -1` commands only share a process when their group names match.
- `--wait-for-single-instance-window-close` makes the `kitty -1` command wait until the window it opened has been closed.

## Set the window class, name and title

Window managers and compositors often use a window's class to apply rules. kitty lets you set these values:

- `--class` (alias `--app-id`), default `kitty`: the app ID on Wayland, or the class part of `WM_CLASS` on X11.
- `--name` (alias `--os-window-tag`), default empty: the window tag on Wayland, or the name part of `WM_CLASS` on X11. On X11, if you leave it empty, the class value is used.
- `-T` (long form `--title`): a fixed title for the OS window. Programs running inside can no longer change it.

```
kitty --class scratchpad -T "Scratch terminal"
```

## Run kitty detached from the terminal

To start kitty detached from the terminal you launched it from, use `--detach`. Add `--detached-log FILE` to collect the detached kitty's standard output and standard error in a file.

## Capture global shortcuts

`--grab-keyboard` asks the system to send all key presses to kitty, including shortcuts your desktop normally handles itself. On Wayland this only works if the compositor supports the keyboard-shortcuts-inhibit protocol.

## Open a remote-control socket

`--listen-on ADDRESS` makes kitty listen for remote-control commands on a socket. Address forms:

- `unix:/tmp/my-kitty` for a Unix socket file,
- `unix:@my-kitty` for a Linux abstract socket,
- `tcp:localhost:12345` for TCP.

Environment variables in the address are expanded, and a relative socket path is placed in the temporary directory. The socket is only opened when `allow_remote_control` in `kitty.conf` is set to `yes`, `socket` or `socket-only`. Other programs then send commands with `kitten @ --to ADDRESS ...`.

## Use the debugging options

These switches help when reporting or tracking down problems:

| Option | What it does |
|---|---|
| `-v`, `--version` | Print the version and exit |
| `--debug-input` (also `--debug-keyboard`) | Log every key and mouse event, including the `native_code` value you can use in `map` |
| `--debug-rendering` (also `--debug-gl`) | Check every OpenGL call for errors and print extra rendering information |
| `--debug-font-fallback` | Log which fallback font is chosen for characters missing from your main font |
| `--dump-commands` | Print the terminal commands kitty receives from the program to standard output |
| `--replay-commands PATH` | Replay a file produced by `--dump-commands` |
| `--dump-bytes PATH` | Save the raw bytes the program writes to a file |

There is no `--debug-config` option in 0.48.2. To inspect the effective configuration, press `ctrl+shift+f6` inside kitty, which runs the `debug_config` action. The old `--watcher` option is deprecated; put `watcher` lines in `kitty.conf` instead.

## Run kittens and helpers through the kitty binary

The `kitty` program accepts a few special first arguments beginning with `+` or `@`:

- `kitty +kitten NAME [args]` runs a kitten, the same as `kitten NAME [args]`.
- `kitty +runpy 'python code'` runs a Python snippet with kitty's modules available.
- `kitty +launch script.py` runs a Python script that can use kitty's code; a name starting with `:` is searched for on your `PATH`.
- `kitty +open URL...` opens URLs or files through kitty.
- `kitty +list-fonts` and `kitty +icat` are older entry points kept for compatibility.
- `kitty @ ...` is passed on to `kitten @ ...`, the remote-control client.

kitty also has internal helpers (`+hold`, `+complete`, `+shebang`) that you normally do not call yourself.

## Use the kitten program

The separate `kitten` program runs kittens directly: `kitten command [options] [args]`. `kitten --help` lists the commands, `kitten CMD -h` shows help for one of them, and `kitten --version` prints its version (0.48.2 in Kilix).

## Environment variables kitty reads

| Variable | Effect |
|---|---|
| `KITTY_CONFIG_DIRECTORY` | Use this directory for configuration, skipping the normal search |
| `KITTY_CACHE_DIRECTORY` | Where kitty keeps cached data; default `$XDG_CACHE_HOME/kitty`, usually `~/.cache/kitty` |
| `KITTY_RUNTIME_DIRECTORY` | Where sockets and other runtime files go; default `$XDG_RUNTIME_DIR`, otherwise a run directory under the cache directory |
| `VISUAL`, `EDITOR` | Editor used to open `kitty.conf` |
| `SHELL` | Shell started when the `shell` option is `.` (its default) |
| `GLFW_IM_MODULE` | Set to `ibus` to use an input method under X11 |
| `KITTY_WAYLAND_DETECT_MODIFIERS` | Any non-empty value makes kitty detect extra XKB modifiers, such as hyper, on Wayland |

Inside `kitty.conf` include lines, `KITTY_OS` is also available and expands to `linux`, `macos` or `bsd`.

## Environment variables kitty sets for programs

Programs running inside kitty can read these:

- `KITTY_PID`: the process ID of the kitty that owns the window. Useful for `kill -SIGUSR1 $KITTY_PID` to reload the configuration.
- `KITTY_LISTEN_ON`: the remote-control socket address, when one applies to the window.
- `KITTY_PIPE_DATA`: set for programs started by `launch --stdin-source`, describing the screen data that was piped in (see `06-launch-and-sessions.md`).

## See also

- `01-getting-started.md` - kitty's building blocks and first steps
- `03-configuration.md` - the `kitty.conf` file and its options
- `04-keyboard-and-mouse.md` - shortcuts and mouse bindings
- `05-tabs-windows-layouts.md` - managing tabs, windows and layouts
- `06-launch-and-sessions.md` - the `launch` action and session files
