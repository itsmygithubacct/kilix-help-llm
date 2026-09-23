# Troubleshooting kitty

This page collects common kitty problems on Linux, each written as the problem you see, why it happens, and how to fix it. It starts with the diagnostic tools built into kitty 0.48.2 and where kitty writes its errors, then covers configuration that seems to be ignored, "unknown terminal" errors over SSH and sudo, shortcuts that do not reach a program, fonts, colours in vim and tmux, transparency, a frozen window, environment differences, memory use, slow startup and remote control that will not connect.

## Diagnostic tools you can use

- **Show the effective configuration:** press `ctrl+shift+f6` (action `debug_config`). kitty opens a report in a pager and also copies it to the clipboard. It lists the kitty version, `uname` output, the window manager or compositor kitty is running under, the OpenGL driver version, the fonts in use, and every option and mapping that differs from the defaults. Paste this when asking for help.
- **Watch keyboard and mouse events:** start kitty with `kitty --debug-input` (also spelled `--debug-keyboard`). Events are printed to standard error as they arrive.
- **See what a key sends:** run `kitten show-key`, optionally with `-m normal|application|kitty|unchanged`.
- **Check font fallback:** `kitty --debug-font-fallback` prints which fallback font kitty picks for characters the main font lacks.
- **Check rendering:** `kitty --debug-rendering` (also `--debug-gl`) checks every OpenGL call and prints rendering details.
- **Low-level escape code debugging:** `kitty --dump-bytes FILE`, `--dump-commands` and `--replay-commands FILE`.
- **Ask the terminal about itself:** `kitten query-terminal` prints the name, version, fonts, colours, opacity and more.
- **See kitty's own environment:** the action `show_kitty_env_vars` (no default key; run it from the command palette, `ctrl+shift+f3`).
- **Check the version:** `kitty --version` prints `kitty 0.48.2` followed by the author's name in this build.

Note: kitty 0.48.2 has no `--debug-config` command-line flag. Older versions had one; use `ctrl+shift+f6` instead.

## Where kitty writes errors

kitty writes its log to standard error, and each line starts with a timestamp in seconds.

- If you started kitty from another terminal, errors appear there.
- If you started it from a desktop launcher, they go wherever your desktop session sends standard error, often the systemd journal or a session log file. The exact place depends on the desktop and is not confirmed here.
- `kitty --detach --detached-log=FILE` sends kitty's output to a file you choose.

A useful habit when something misbehaves: start a second kitty from a terminal you already have open, so you can read its messages.

## Problem: kitty shows an error window about configuration

**Cause:** one or more lines in `kitty.conf` (or an included file) could not be understood.

**Fix:** read the error window. kitty groups the bad lines by file and shows the line number, the error and the line itself. kitty keeps running with every valid line, so the rest of your settings still apply. Fix the listed lines, then reload with `ctrl+shift+f5`. Open the config file quickly with `ctrl+shift+f2`.

## Problem: my configuration changes are ignored

**Possible causes and fixes:**

- **kitty is reading a different file.** kitty uses the first file found among `$XDG_CONFIG_HOME/kitty/kitty.conf`, `~/.config/kitty/kitty.conf` and `$XDG_CONFIG_DIRS/kitty/kitty.conf`. If `KITTY_CONFIG_DIRECTORY` is set, kitty uses that directory only. A system-wide `/etc/xdg/kitty/kitty.conf`, if present, is loaded first with lower priority. Press `ctrl+shift+f6` to see what kitty actually applied.
- **Command-line overrides win.** `kitty -c FILE` loads other files (several `-c` are merged in order; `-c NONE` loads none), and `kitty -o name=value` overrides single options.
- **The option cannot be reloaded.** Some settings, such as `listen_on`, `dynamic_background_opacity` and `linux_display_server`, only take effect when kitty starts. Others, like `scrollback_lines`, only affect new windows after a reload.
- **Syntax slips.** A `#` starts a comment only at the beginning of a line. A line that starts with `\` continues the previous line. `include` paths are relative to the file that contains them.

To test with a clean setup, start `kitty --config NONE`. It is not confirmed whether this also skips extra configuration layered on by Kilix.

**In Kilix:** the `kilix` launcher loads Kilix's own shipped `kitty.conf`, which adds bindings such as the right-click context menu. If kitty inside Kilix behaves differently from upstream kitty, check `ctrl+shift+f6` for these extra settings.

## Problem: "unknown terminal type" or "xterm-kitty" errors on another machine

**Symptoms:** after logging in to a server, programs complain that the terminal `xterm-kitty` is unknown, or backspace and arrow keys print odd characters.

**Cause:** kitty sets `TERM=xterm-kitty` (from the `term` option), and the server has no terminfo description for it.

**Fix:** log in with the ssh kitten, which copies the terminfo and turns on shell integration for you:

```
kitten ssh user@server
```

Changing `term` to something else is not recommended; it breaks kitty features.

## Install kitty's terminfo on a server by hand

If you cannot use the ssh kitten, copy the terminfo yourself:

```
infocmp -a xterm-kitty | ssh user@server tic -x -o \~/.terminfo /dev/stdin
```

- If the server's `tic` cannot read standard input, or a proxy gets in the way, save the `infocmp` output to a file, copy the file over, and run `tic` on the server.
- If the server has no `tic` at all, copy your local terminfo file to `~/.terminfo/x/xterm-kitty` on the server.
- Many distributions package it as `kitty-terminfo`; install that on the server as root.
- On systems that use termcap (such as FreeBSD), append the output of `infocmp -CrT0 xterm-kitty` to `/usr/share/misc/termcap` and run `cap_mkdb /usr/share/misc/termcap`.

## Problem: terminal errors only under `sudo` or `su`

**Cause:** sudo filters out the `TERMINFO` variable, so programs run as root cannot find kitty's terminfo.

**Fixes (pick one):**

- Install the `kitty-terminfo` package system-wide.
- Run `sudo visudo` and add `Defaults env_keep += "TERM TERMINFO"`.
- Pass it explicitly, perhaps through an alias: `sudo TERMINFO="$TERMINFO" command`.

Shell integration already wraps `sudo` to handle this, unless you set `no-sudo` in `shell_integration` (see 08-shell-integration.md).

## Problem: wide characters break the prompt

**Cause:** the locale is not UTF-8, so the shell miscounts double-width characters.

**Fix:** set a UTF-8 locale through `LANG` or `LC_ALL`, for example `LANG=en_US.UTF-8`.

## Problem: a key combination does not work in a program

**Diagnose:** run `kitten show-key -m kitty` and press the combination.

- **The key is shown:** kitty is passing it on, so the program does not understand it (for example because it does not support kitty's keyboard protocol). Report it to the program's authors.
- **Nothing is shown:** kitty has that key bound to one of its own actions. Free it for programs with `map KEY no_op`, for example:

```
map ctrl+shift+left no_op
```

For a full picture of every event kitty receives, start it with `kitty --debug-input`.

## Make a key send something else

Map a key to a different key press with `send_key`:

```
map alt+s send_key ctrl+s
map f5 combine : send_key ctrl+c : send_key up : send_key enter
```

To type text instead, use the `send_text` action.

**In Kilix:** plain right-click opens Kilix's context menu (`show_context_menu`) instead of extending the selection as upstream kitty does. If right-click seems to behave differently from kitty's documentation, this is why (see 10-clipboard-and-links.md).

## Problem: my font does not appear or looks wrong

**Cause:** kitty only uses monospaced, scalable fonts. Bitmap fonts and proportional fonts are left out.

**Fix:** pick fonts with `kitten choose-fonts`, which shows previews, supports variable fonts and font features, and writes the result to `kitty.conf`. In 0.48.2, `kitty +list-fonts` opens the same picker; there is no plain text list. The default `font_family` is `monospace`.

To check whether fontconfig sees a font as usable, run:

```
fc-list : family spacing outline scalable
```

Usable fonts show `spacing=100` or `spacing=90`, `outline=True` and `scalable=True`. If fontconfig gets the spacing wrong, add a `<match target="scan">` rule to `~/.config/fontconfig/fonts.conf` that sets `spacing` to `100` for that family, then run `fc-cache -r`.

## Problem: symbols or icons are tiny, cut off or missing

- **Patched "Nerd Fonts":** you do not need them. kitty includes a symbols font and uses it for icons your main font lacks. If an installed patched font takes over, force the bundled one with `symbol_map` for the private-use ranges and the font name `Symbols Nerd Font Mono`.
- **Icons squeezed into one cell:** private-use characters take one cell unless followed by a space or an en-space (U+2002), in which case they get two. `narrow_symbols` forces chosen code points to a set width; its default is `U+E0A0-U+E0A3,U+E0C0-U+E0C7 1`. Since kitty 0.40, programs can also choose widths through the text-sizing protocol.
- **Bold or italic letters clipped:** the bold or italic face is wider than the regular one, which is a bug in the font.
- **Wrong fallback font:** start kitty with `--debug-font-fallback` to see what is chosen.

## Problem: vim shows the wrong background colour

**Cause:** kitty does not support background colour erase (BCE), which some vim setups assume.

**Fix:** add `let &t_ut=''` to `~/.vimrc`, before any `colorscheme` line, and do not change `term` afterwards. More generally, use a proper vim colour scheme rather than relying on the terminal theme.

## Problem: colours or keys break in tmux

- Very old tmux (for example 1.8) prints garbage on key presses. Upgrade tmux.
- Moving a tmux session between terminals with different `TERM` values breaks it. Restart tmux.
- Many kitty extras (styled underlines, notifications, text sizing, the keyboard protocol, file transfer, the ssh kitten, shell integration) may or may not work through tmux.
- Images in tmux: `kitten icat` detects tmux and uses passthrough with Unicode placeholders. Other programs (nvim, ranger) must support placeholders themselves.
- kitty's own tabs, windows and sessions cover most of what tmux is used for; tmux remains useful mainly for keeping sessions alive on remote machines.

## Change colours without restarting

- `kitten themes` to pick a theme.
- `map KEY set_colors --configured FILE.conf` to switch colour files with a key.
- `kitten @ set-colors` from scripts.
- `color_scheme` in `ssh.conf` for a different theme per host.

## Problem: a gap or border at the window edge

**Cause:** the window size is rarely an exact multiple of the character cell size, and `window_padding_width` adds space as well. Full-screen programs that paint their own background make the gap obvious.

**Fix:** the clean solution is for the program to set the terminal's default background colour (through an escape code) instead of painting its own background over the cells.

## Problem: background transparency does not work

`background_opacity` (default `1.0`, range 0 to 1) makes the background see-through, but:

- **No compositor:** on X11 a compositor must be running. Wayland compositors handle it themselves.
- **Programs paint their own background:** only cells using the default background become transparent. An editor theme with its own background stays solid. Set the colour in kitty instead, or use `transparent_background_colors` (up to 7 `color@opacity` entries; needs `background_opacity` below 1).
- **Changing it at runtime fails:** you need `dynamic_background_opacity yes`, which only takes effect at startup. Then `ctrl+shift+a` followed by `m` (more opaque by 0.1), `l` (less opaque), `1` (fully opaque) or `d` (back to default), or `kitten @ set-background-opacity`.
- **Background images:** opacity does not apply to `background_image`; use an image with transparency instead.
- Opacity below 1 costs some speed.

`background_blur` (default `0`) blurs what is behind the window when opacity is below 1, on Wayland compositors that support blur. High values can cause slowness or artefacts; staying at about 64 or below is reasonable.

To force the X11 or Wayland backend, set `linux_display_server x11` or `wayland` (default `auto`); this needs a restart.

## Problem: the window froze after printing a binary file

**Cause:** binary data can begin a control sequence that never ends, so kitty waits for the rest of it.

**Fix:** press `ctrl+shift+delete`, which resets the terminal (`clear_terminal reset active`). Next time, view unknown files with `cat -v`.

## Problem: things work in a terminal-started kitty but not a desktop-started one

**Cause:** kitty started from the desktop gets the desktop's environment, not the one your shell startup files set up. Typical differences are `PATH`, `LANG`, `LC_*`, `XDG_*` and `KITTY_CONFIG_DIRECTORY`.

**Fix:** set variables in `kitty.conf` with `env`, or have kitty read them from your login shell (since 0.43.2; POSIX shells and fish; globs allowed):

```
env PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
env read_from_shell=PATH LANG LC_* XDG_* EDITOR VISUAL
```

`read_from_shell` makes startup slower. Check what kitty sees with the `show_kitty_env_vars` action.

## Problem: new windows do not open in the current directory

**Fix:** map keys to launch with the current directory:

```
map ctrl+alt+enter launch --cwd=current
map ctrl+alt+t launch --cwd=current --type=tab
```

Or use the actions `new_window_with_cwd` and `new_tab_with_cwd`. `--cwd=last_reported` follows the directory reported by the shell and needs shell integration.

## Problem: kitty seems to use a lot of memory

**Cause:** tools like `top` overstate memory, because the memory allocator keeps freed blocks for reuse. The GPU driver and per-thread allocator areas also account for some. A large `scrollback_lines` really does use more memory.

**Check:** to look for real leaks, run `PYTHONMALLOC=malloc valgrind --tool=massif kitty`. With glibc, setting `MALLOC_MMAP_THRESHOLD_=64` makes freed memory show up as returned.

## Problem: kitty is slow to start

**Normal:** kitty starts in about the same time as other GPU terminals, roughly 100 ms.

**Causes of slow starts:**

- Laptops with two GPUs may need to wake the dedicated GPU, which can take seconds. A hardware-specific workaround is to force the Mesa/integrated GPU, for example with `__EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json` and a `MESA_LOADER_DRIVER_OVERRIDE` setting suited to your hardware.
- `env read_from_shell` runs your shell at startup and adds time.

## Problem: I want a terminal on a global hotkey

**Fix:** bind `kitten quick-access-terminal` to a global shortcut in your desktop or window manager (see 11-kittens.md). On GNOME under Wayland this does not work, because GNOME lacks the layer-shell support that panels need.

## Problem: `kitten @` cannot connect

- **Remote control is off:** `allow_remote_control` defaults to `no`.
- **Scripts outside kitty:** they need a socket. Set `listen_on` (or start kitty with `--listen-on`) and set `allow_remote_control` to `yes`, `socket` or `socket-only`, then pass the address with `kitten @ --to ADDRESS`. Remember kitty adds its process ID to the address unless you place `{kitty_pid}` yourself.
- **Inside kitty:** no address is needed; `KITTY_LISTEN_ON` or the terminal itself is used.
- **Password mode over SSH:** the remote side needs `KITTY_PUBLIC_KEY` (the ssh kitten forwards it) and both clocks must be within a few minutes of each other.

See 07-remote-control.md for details.

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
- 11-kittens.md
