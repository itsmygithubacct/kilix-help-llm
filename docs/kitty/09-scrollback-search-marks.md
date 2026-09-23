# Scrollback, searching, clearing and marks

Everything that scrolls off the top of a kitty window goes into the scrollback, a history buffer you can scroll back through with the keyboard, the mouse or the scrollbar. For heavier reading and searching, kitty opens the scrollback in a pager program (`less` by default) in an overlay on top of the window. This page covers how much history kitty keeps, the scroll keys, the scrollbar, viewing and searching scrollback in the pager, sending scrollback to other programs, the different ways to clear the screen, and marks: coloured highlighting of text that matches a pattern, with keys to jump between the highlighted lines.

## Set how much scrollback kitty keeps

The `scrollback_lines` option sets the number of lines kept per window. The default is `2000`.

```
scrollback_lines 10000
```

- Memory is allocated only as the history fills up.
- A negative number means practically unlimited.
- Very large values use more memory and slow things down. If you only need long history for occasional reading, consider the pager history buffer below instead.
- After a configuration reload, the new value applies only to windows opened afterwards.

## Keep extra history just for the pager

`scrollback_pager_history_size` adds a second, compact history buffer that is used only when you open the scrollback in the pager. It is not used when you scroll inside the window itself. The value is in megabytes and the default `0` turns it off.

```
scrollback_pager_history_size 20
```

Text in this buffer is stored as UTF-8, so one megabyte holds about 10,000 lines of 100 plain ASCII characters. The maximum is 4 GB, and as with `scrollback_lines`, a reload only affects new windows.

## Scroll with the keyboard

Default Linux keys:

| Keys | Action |
|---|---|
| `ctrl+shift+up` or `ctrl+shift+k` | one line up (`scroll_line_up smooth`) |
| `ctrl+shift+down` or `ctrl+shift+j` | one line down (`scroll_line_down smooth`) |
| `ctrl+shift+page_up` | one page up (`scroll_page_up`) |
| `ctrl+shift+page_down` | one page down (`scroll_page_down`) |
| `ctrl+shift+home` | to the top of the scrollback (`scroll_home`) |
| `ctrl+shift+end` | back to the bottom (`scroll_end`) |
| `ctrl+shift+z` | previous shell prompt (`scroll_to_prompt -1`) |
| `ctrl+shift+x` | next shell prompt (`scroll_to_prompt 1`) |

The `smooth` argument makes line scrolling animated. The prompt keys need shell integration (see 08-shell-integration.md).

Scroll actions work on the main screen only. Full-screen programs such as editors use the alternate screen, which has no kitty scrollback, so these keys do nothing there.

## Scroll by any amount

To scroll by an amount no built-in action offers, map a key to the `scroll-window` remote control command. This works through a key mapping even when remote control is otherwise disabled:

```
map ctrl+alt+up   remote_control scroll-window 0.5p-
map ctrl+alt+down remote_control scroll-window 0.5p
```

The amount can be `start`, `end`, or a number followed by a unit: `l` for lines (the default), `p` for pages, `u` for unscroll (see the end of this page) and `r` for prompts. A trailing `-` means up. So `3` is three lines down, `0.5p-` is half a page up, and `1r-` is the previous prompt.

## Tune mouse wheel and touchpad scrolling

- `wheel_scroll_multiplier` (default `5.0`) multiplies scrolling from ordinary, low-precision mouse wheels. A negative value reverses the direction.
- `wheel_scroll_min_lines` (default `1`) is the minimum number of lines per wheel step. A negative value means always scroll exactly that many.
- `touch_scroll_multiplier` (default `1.0`) applies to high-precision devices such as touchpads on Wayland.

## Pull history back when a window grows

With `scrollback_fill_enlarged_window yes` (default `no`), making a window taller fills the new space with lines taken back from the scrollback, instead of leaving it blank.

## Control the scrollbar

kitty 0.48 draws its own scrollbar. The `scrollbar` option decides when it appears:

- `scrolled` (default) - once you have scrolled back.
- `hovered` - when the mouse is at the right edge of the window.
- `scrolled-and-hovered` - in either case.
- `always` - whenever there is any scrollback.
- `never` - not at all.

With the defaults `scrollbar_interactive yes` and `scrollbar_jump_on_click yes`, you can drag the handle and click the track to jump. Appearance options and their defaults: `scrollbar_width 0.5`, `scrollbar_hover_width 1`, `scrollbar_radius 0.3`, `scrollbar_gap 0.1`, `scrollbar_min_handle_height 1`, `scrollbar_hitbox_expansion 0.25`, `scrollbar_handle_opacity 0.5`, `scrollbar_track_opacity 0`, `scrollbar_track_hover_opacity 0.1`, `scrollbar_handle_color foreground` and `scrollbar_track_color foreground`. Width, radius and gap are measured in cell widths.

The older `scrollback_indicator_opacity` option is deprecated; use the scrollbar options instead.

## Open the scrollback in a pager

Press `ctrl+shift+h` (action `show_scrollback`). kitty opens the pager in an overlay window on top of the current one, with colours and text styles preserved. Quit the pager to return.

The pager command comes from `scrollback_pager`. The default is:

```
scrollback_pager less --chop-long-lines --RAW-CONTROL-CHARS +INPUT_LINE_NUMBER
```

Rules for the pager:

- kitty writes the scrollback to the pager's standard input, so the pager must cope with ANSI colour (SGR) codes.
- When the program is `less`, kitty also adds `-+F` so `less` does not exit straight away on short content.
- The pager starts in the working directory of the window's program.
- If the program cannot be found on `PATH`, kitty logs an error and uses `less`.

## Use pager placeholders

kitty replaces these words anywhere in the `scrollback_pager` command:

- `INPUT_LINE_NUMBER` - the line that should be at the top of the pager, so the view opens where you were.
- `CURSOR_LINE` - the cursor's row, counting from 1, or `0` when there is no cursor (for example when viewing a single command's output).
- `CURSOR_COLUMN` - the cursor's column, counting from 1, or `0`.

A custom pager setup might look like this:

```
scrollback_pager less -R +INPUT_LINE_NUMBER
```

Neovim 0.12 or newer can act as the pager (it uses `nvim_open_term`), and a third-party plugin, kitty-scrollback.nvim, offers a richer Neovim-based view.

## View a single command's output

With shell integration active you can open just part of the history:

- `ctrl+shift+g` - output of the last command (`show_last_command_output`).
- `ctrl+shift` + right-click on any output - that command's output.
- `show_first_command_output_on_screen`, `show_last_visited_command_output` and `show_last_non_empty_command_output` - available as actions without default keys.

## Send scrollback to another program

Use `launch` with `--stdin-source` to pipe history into any program:

```
map f10 launch --type=overlay --stdin-source=@screen_scrollback grep --color=always -i error
map f11 launch --type=tab --stdin-source=@last_cmd_output --stdin-add-formatting less -R
```

Other sources include `@screen`, `@selection`, `@alternate` and `@alternate_scrollback` (the full list is in 07-remote-control.md). The receiving program gets a `KITTY_PIPE_DATA` variable of the form `scrolled_by:cursor_x,cursor_y:lines,columns`.

The older `pipe` action still exists, but `launch --stdin-source` is the recommended way.

## Search the scrollback

Press `ctrl+shift+/` (action `search_scrollback`). kitty opens the scrollback pager and types `/` into it, which starts a search in `less` and in vim-like pagers. If you had text selected, kitty types that text as the search term and presses Enter for you, so selecting a word and pressing `ctrl+shift+/` jumps straight to its occurrences.

This relies on the pager starting a search when it receives `/`. If you use a pager that searches with a different key, `search_scrollback` will not work as expected.

As far as the fact sheets for this version show, kitty 0.48.2 has no separate search box drawn over the terminal; searching goes through the pager. (This is not fully confirmed.)

## Clear the screen or the scrollback

`ctrl+shift+delete` runs `clear_terminal reset active`, which resets the terminal and wipes both the screen and the scrollback. It is also the fix when a window stops responding after printing binary data.

The general form is `clear_terminal MODE TARGET`, where TARGET is `active` (current window) or `all` (every window). Modes:

| Mode | What happens |
|---|---|
| `reset` | full reset, clears screen and scrollback |
| `clear` | clears the screen |
| `scrollback` | clears only the scrollback |
| `scroll` | pushes the screen contents into scrollback, leaving a clean screen |
| `to_cursor` | clears everything above the prompt, moves the prompt to the top, discards the cleared lines |
| `to_cursor_scroll` | like `to_cursor`, but the cleared lines go into scrollback |
| `last_command` | removes the most recent command together with what it printed (requires shell integration) |

Example mappings:

```
map ctrl+alt+l clear_terminal scroll active
map ctrl+alt+k clear_terminal scrollback active
```

`scroll_prompt_to_top` and `scroll_prompt_to_bottom` move the current prompt without discarding anything (main screen only).

## Highlight text with marks

Marks colour every occurrence of a pattern in a window, which makes errors or keywords stand out in busy output. There are three mark groups, numbered 1 to 3, each with its own colours. Group numbers outside that range are clamped into it.

A marker is set with the `toggle_marker` action:

```
map f4 toggle_marker text 1 ERROR
```

Pressing the key again with the same specification turns the marker off.

## Marker types

The first word after `toggle_marker` picks how patterns are matched:

- `text` - plain substring, case sensitive.
- `itext` - plain substring, case insensitive.
- `regex` - Python regular expression.
- `iregex` - case-insensitive regular expression.
- `function` - your own Python code (see below).

For the text and regex types, the rest of the line is pairs of group number and pattern. An odd number of words is an error. To mark several things at once:

```
map f5 toggle_marker itext 1 error 2 warning 3 deprecated
map f6 toggle_marker iregex 1 \\bfail(ed|ure)?\\b 2 \\btimeout\\b
```

Backslashes in a regex must be doubled in `kitty.conf`, as in the second line.

## How marks behave

- Matching is done one line at a time; a pattern cannot span two lines.
- Matches are recomputed only when a line changes.
- A window has one marker at a time. Setting a new marker replaces the old one, so to highlight several patterns, put them all in one marker.

## Write a marker function in Python

With the `function` type, give the path to a Python file. Relative paths are looked up in the kitty config directory. The file defines `marker(text)`, a generator that yields `(start, end, group)` tuples: character positions within the line and the group to colour them with.

```
map f7 toggle_marker function mymarker.py
```

## Create markers on the fly

- The `create_marker` action asks you to type a marker specification (same syntax as `toggle_marker`, with input history).
- The `remove_marker` action removes the window's marker.

Neither has a default key. From scripts, use `kitten @ create-marker TYPE SPEC...` and `kitten @ remove-marker`, or start a window with a marker already set using `launch --marker SPEC`.

## Change mark colours

Defaults:

```
mark1_foreground black
mark1_background #98d3cb
mark2_foreground black
mark2_background #f2dcd3
mark3_foreground black
mark3_background #f274bc
```

## Jump between marked lines

`scroll_to_mark` scrolls to marked lines. It has no default key.

- No arguments: the previous mark of any group.
- `prev` (or `previous`): the first marked line above the current top of the screen.
- `next`: the first marked line below the current bottom of the screen.
- A group number limits it to that group; `0` means any group. A single number on its own means "previous mark in that group".

```
map ctrl+alt+p scroll_to_mark prev
map ctrl+alt+n scroll_to_mark next
map ctrl+alt+1 scroll_to_mark next 1
```

## Unscroll: bring back text a menu pushed away

Shell completion menus sometimes push lines off the screen. kitty supports an "unscroll" escape code extension (since 0.20.2): `CSI <n> + T` scrolls the screen down like the standard scroll-down code, but refills the top lines from the scrollback rather than leaving them blank. If there is no scrollback (for example on the alternate screen), blank lines are used. mintty supports the same code.

You can do this by hand with remote control: `kitten @ scroll-window 3u` unscrolls three lines.

## See also

- 01-getting-started.md
- 02-command-line.md
- 03-configuration.md
- 04-keyboard-and-mouse.md
- 05-tabs-windows-layouts.md
- 06-launch-and-sessions.md
- 07-remote-control.md
- 08-shell-integration.md
- 10-clipboard-and-links.md
- 11-kittens.md
- 12-troubleshooting.md
