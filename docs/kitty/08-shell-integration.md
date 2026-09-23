# Shell integration: prompts, command output and working directories

Shell integration is a small piece of shell code that kitty loads into bash, zsh or fish when a new shell starts. That code tells kitty where each prompt begins, when a command starts and finishes, which directory the shell is in, and what title to show. With that knowledge kitty can jump between prompts, show the output of a single command in a pager, open new windows in the same directory, and more. It is on by default for supported shells. This page explains what it gives you, how to turn individual parts off, how kitty loads it, how to load it by hand in places kitty cannot reach (tmux, containers, sub-shells), and the helper commands `clone-in-kitty`, `edit-in-kitty` and `kitten run-shell`.

## What shell integration gives you

Shell integration appeared in kitty 0.24.0. With it active you get:

- **Last command output in a pager:** `ctrl+shift+g` (action `show_last_command_output`).
- **Prompt-to-prompt scrolling:** `ctrl+shift+z` jumps to the previous prompt and `ctrl+shift+x` to the next.
- **Output of any earlier command:** hold `ctrl+shift` and right-click on the output to open it in the pager.
- **Click to move the cursor:** clicking inside the command you are typing moves the text cursor to that spot.
- **Useful titles:** window and tab titles follow the current directory or the running command.
- **Bar cursor at the prompt:** the cursor becomes a thin bar while you edit a command.
- **Clean resizing:** when you resize a window, kitty clears the prompt and lets the shell draw it again, so you do not get broken prompt fragments.
- **Tab completion for the `kitty` command** itself.
- **Fewer close prompts:** when confirming whether to close, kitty does not count windows that are just sitting at a prompt (this applies with the default negative `confirm_os_window_close` of `-1`).
- **`clone-in-kitty` and `edit-in-kitty`** shell commands (described below).

Several other features depend on it: `launch --cwd=last_reported`, the command-output extents of `kitten @ get-text` such as `last_cmd_output`, and opening new windows on the same remote host through the ssh kitten.

## Which shells are supported

kitty loads shell integration automatically for `bash`, `zsh` and `fish`. bash must be version 4 or newer; an older bash prints a warning and runs without integration.

kitty decides which shell it is starting by looking at the program name of the configured shell. The `shell` option defaults to `.`, meaning "use `$SHELL`, or the user's login shell".

Other shells have third-party integrations: xonsh, Nushell (set `$env.config.shell_integration = true` in `config.nu`), and the IPython/Jupyter console (through a patch).

## Turn shell integration off, or switch off single features

The `shell_integration` option controls everything. Its default is `enabled`.

To turn it off completely:

```
shell_integration disabled
```

With `disabled`, kitty does not touch the shell's startup environment and does not set `KITTY_SHELL_INTEGRATION`.

To keep integration but drop particular features, list one or more of these words, separated by spaces:

| Word | Effect |
|---|---|
| `no-rc` | kitty does not change how the shell starts; you load the integration yourself. `KITTY_SHELL_INTEGRATION` is still set. |
| `no-cursor` | the cursor keeps its normal shape at the prompt |
| `no-title` | no title updates (fish uses its own title logic regardless) |
| `no-cwd` | the working directory is not reported (fish's own reporting still happens) |
| `no-prompt-mark` | prompts are not marked, which also disables jumping between prompts, viewing command output and click-to-move (fish always marks prompts, so this does nothing there) |
| `no-complete` | no completion for the `kitty` command (fish ships its own, so no effect there) |
| `no-sudo` | kitty does not wrap `sudo` to make its terminfo available; use this if your sudo rules forbid setting environment variables on the command line |

Example that keeps prompt marks but leaves your cursor and titles alone:

```
shell_integration no-cursor no-title
```

Changes to this option apply to shells started afterwards. Whether a reload affects shells that are already running is not confirmed; assume it does not, and open a new window to test.

## How kitty loads shell integration automatically

kitty does not edit your dotfiles. Instead it adjusts how each shell starts:

- **zsh:** kitty points `ZDOTDIR` at its own directory. kitty's `.zshenv` there puts your original `ZDOTDIR` back, runs your own `.zshenv`, and then loads the integration.
- **fish:** kitty adds its integration directory to the front of `XDG_DATA_DIRS` for that fish process only, and it is removed again after startup. No files are changed.
- **bash:** kitty starts bash in POSIX mode with `ENV` pointing at kitty's `kitty.bash`. That script switches POSIX mode off again and runs your normal bash startup files.

kitty passes the value of `shell_integration` in the `KITTY_SHELL_INTEGRATION` environment variable. The integration script reads it and then removes it from the environment.

The scripts live under `$KITTY_INSTALLATION_DIR/shell-integration/`, in subdirectories named `bash`, `zsh` and `fish`.

## When you need to set up shell integration manually

Automatic loading only reaches the shell kitty itself starts. You need manual setup for:

- shells inside tmux or screen,
- shells started from another shell (sub-shells),
- shells inside containers.

The steps are: disable automatic loading in `kitty.conf`, then add a few lines to your shell's startup file that load the script whenever `KITTY_INSTALLATION_DIR` is set.

```
shell_integration disabled
```

`KITTY_SHELL_INTEGRATION` accepts the same values as the option. Leave it unset to keep integration off.

## Manual setup for bash

Add to `~/.bashrc`:

```
if [[ -n "$KITTY_INSTALLATION_DIR" ]]; then
    export KITTY_SHELL_INTEGRATION="enabled"
    source "$KITTY_INSTALLATION_DIR/shell-integration/bash/kitty.bash"
fi
```

## Manual setup for zsh

Add to `~/.zshrc`:

```
if [[ -n "$KITTY_INSTALLATION_DIR" ]]; then
    export KITTY_SHELL_INTEGRATION="enabled"
    autoload -Uz -- "$KITTY_INSTALLATION_DIR"/shell-integration/zsh/kitty-integration
    kitty-integration
    unfunction kitty-integration
fi
```

## Manual setup for fish

Add to `~/.config/fish/config.fish`:

```
if set -q KITTY_INSTALLATION_DIR
    set --global --export KITTY_SHELL_INTEGRATION enabled
    source "$KITTY_INSTALLATION_DIR/shell-integration/fish/vendor_conf.d/kitty-shell-integration.fish"
    set --prepend fish_complete_path "$KITTY_INSTALLATION_DIR/shell-integration/fish/vendor_completions.d"
end
```

## Shell integration inside containers

In a container, kitty's files are not installed. Copy the `shell-integration` scripts into the container, set `KITTY_INSTALLATION_DIR` to the directory that holds them, and follow the manual steps above. The easier route is usually `kitten run-shell`, described next.

## Start an integrated shell anywhere with `kitten run-shell`

`kitten run-shell` (since kitty 0.29.0) starts a shell with shell integration switched on. By default it uses the parent shell if it recognises it, otherwise the `shell` option. If you give it a command, that command runs first and the shell starts afterwards.

```
kitten run-shell [options] [command ...]
```

Options:

- `--shell=PATH` - the shell to run (default `.`).
- `--shell-integration=VALUE` - same values as the `shell_integration` option.
- `--env KEY=VALUE` - set a variable (repeatable); a key without `=` removes it.
- `--cwd DIR` - start in this directory.
- `--inject-self-onto-path` - `always` (default), `never` or `unless-root`.

**Containers:** put the standalone `kitten` binary somewhere on the container's `PATH`, then:

```
docker exec -ti mycontainer kitten run-shell --shell=/bin/bash
```

This also makes kitty's terminfo available inside the container.

`kitten run-shell` also works on remote hosts that do not have kitty installed, as long as you connected with the ssh kitten.

## Shell integration over SSH

Connecting with `kitten ssh HOST` gives the remote shell full shell integration automatically, and copies kitty's terminfo too (see 11-kittens.md). The alternative is to copy the integration scripts to the remote host and set them up manually as shown above.

If you use `new_window_with_cwd` together with the ssh kitten, new windows open already logged into the same host. This needs the working directory to be reported, so it does not work with `no-cwd`.

## Copy your shell into a new window with `clone-in-kitty`

`clone-in-kitty` is a shell function provided by shell integration. It opens a new kitty window that has the same environment variables and working directory as the shell you run it in. It works over the ssh kitten too.

It takes most `launch` options:

```
clone-in-kitty --type=tab --title "second shell"
```

It ignores `--allow-remote-control`, `--copy-cmdline`, `--copy-env`, `--stdin-source`, `--marker` and `--watcher`.

## Keep virtual environments when cloning

The `clone_source_strategies` option decides how the cloned shell rebuilds your environment. Default: `venv,conda,env_var,path`. The first strategy that applies is used:

- `venv` runs `$VIRTUAL_ENV/bin/activate`.
- `conda` runs `conda activate $CONDA_DEFAULT_ENV`.
- `env_var` evaluates the shell code stored in `KITTY_CLONE_SOURCE_CODE`.
- `path` sources the file named in `KITTY_CLONE_SOURCE_PATH`.

## Edit a file in a new window with `edit-in-kitty`

`edit-in-kitty` (a shortcut for `kitten edit-in-kitty`) opens a file in your editor in a new kitty window. Over the ssh kitten, it edits a remote file with your local editor.

```
edit-in-kitty +42 src/main.c
edit-in-kitty --type=tab notes.md
```

- `+N` opens at line N (works with vim, neovim, emacs, nano and micro).
- It accepts launch-style options such as `--type`.
- The editor comes from the `editor` option. Its default `.` means `$VISUAL`, then `$EDITOR`, then whatever the shell reported, then a list of known editors.

For safety, only the configured editor is run with the file path, environment variables on its command line are removed, and color settings from files are not allowed.

To use it for root-owned files, set `SUDO_EDITOR="kitten edit-in-kitty"` and then run `sudoedit FILE` (or `sudo -e FILE`).

## Actions that use shell integration

These actions need prompt marks (so `no-prompt-mark` must not be set):

- `show_last_command_output` - default `ctrl+shift+g`.
- `scroll_to_prompt N [OFFSET]` - N below 0 goes back, above 0 goes forward, 0 returns to the prompt last jumped to. OFFSET is how many lines to show above the prompt (default 0). Defaults: `ctrl+shift+z` is `scroll_to_prompt -1`, `ctrl+shift+x` is `scroll_to_prompt 1`.
- `show_last_visited_command_output` - output below the prompt you last jumped to or the output you last clicked.
- `show_first_command_output_on_screen` and `show_last_non_empty_command_output`.
- `copy_last_command_output` - copies the last non-empty output to the clipboard.
- `scroll_prompt_to_top [y]` - moves the current prompt to the top; `y` avoids pushing the lines above into scrollback. `scroll_prompt_to_bottom` does the reverse.
- `clear_terminal last_command active` - erases the last command and its output. It has no default key on Linux.

Mouse actions: `mouse_show_command_output` (default `ctrl+shift` + right-click) and `mouse_select_command_output`, which you might bind like this:

```
mouse_map right press ungrabbed mouse_select_command_output
```

**In Kilix:** plain right-click is already bound to the Kilix context menu (see 10-clipboard-and-links.md), so binding `mouse_select_command_output` to plain right-click replaces that menu.

## Open windows and tabs in the current directory

`new_window_with_cwd`, `new_tab_with_cwd` and `new_os_window_with_cwd` open a new window, tab or OS window in the active window's working directory. For example:

```
map ctrl+alt+enter new_window_with_cwd
map ctrl+alt+t new_tab_with_cwd
```

## For developers: the escape codes involved

Shell integration uses OSC 133 prompt marking, compatible with the style used by iTerm2 and WezTerm. `133;A` is sent before the main prompt, `133;A;k=s` before a continuation prompt, `133;C` just before a command runs, and `133;D;<exit status>` after it finishes. kitty understands extra fields on `A` (`redraw=0`, `special_key=1`, `k=s`, `click_events=1` or `2`) and on `C` (`cmdline=` or `cmdline_url=`).

## See also

- 01-getting-started.md
- 02-command-line.md
- 03-configuration.md
- 04-keyboard-and-mouse.md
- 05-tabs-windows-layouts.md
- 06-launch-and-sessions.md
- 07-remote-control.md
- 09-scrollback-search-marks.md
- 10-clipboard-and-links.md
- 11-kittens.md
- 12-troubleshooting.md
