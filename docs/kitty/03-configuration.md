# Configuring kitty with kitty.conf

kitty 0.48.2, as shipped in Kilix on Linux, is configured through one plain-text file, `kitty.conf`. This guide explains the file's syntax, how to split a configuration across several files with the include directives, how to override settings for a single run, what happens when kitty reloads the file, and then walks through the main groups of options - fonts, cursor, scrollback, mouse and URLs, performance, bell, window geometry, the tab bar, colours and themes, advanced settings and Linux-specific settings - giving each useful option with its default value.

## Write a setting in kitty.conf

Each line of `kitty.conf` holds one setting: the option name, a space, then the value.

```
font_size 13
scrollback_lines 10000
```

A few syntax rules to remember:

- A line is a comment only when its very first character is `#`. You cannot put a comment at the end of a setting line.
- To continue a long value on the next line, start that next line with `\`. kitty removes the leading whitespace and the backslash and joins the lines.
- If the same option appears twice, the later line wins. This matters when you include a theme file: put your own colour tweaks after the `include` line so they take effect.

The file normally lives at `~/.config/kitty/kitty.conf`. Press `ctrl+shift+f2` to open it in your editor.

## Split kitty.conf into several files

kitty offers four ways to pull other content into `kitty.conf`:

- `include PATH` reads another file. A relative path is taken relative to the directory of the file containing the `include`. Environment variables are expanded, so `include ${USER}.conf` loads a per-user file.
- `globinclude PATTERN` reads every file matching a shell glob pattern, relative to the configuration directory, in sorted order. For instance `globinclude conf.d/*.conf`.
- `envinclude PATTERN` reads the contents of every environment variable whose name matches the pattern, such as `envinclude MYKITTY_*`.
- `geninclude PROGRAM` runs a program and reads its output as configuration. The program must be executable. Python scripts run inside kitty's own interpreter, which is the fastest option.

The variable `KITTY_OS` expands to `linux`, `macos` or `bsd` in include paths, so `include os-${KITTY_OS}.conf` picks a per-platform file.

## Override settings without editing the file

You can set options on the command line with `-o name=value`, repeated as often as needed, for example `kitty -o font_size=18`. You can also give several configuration files with repeated `-c` options; they are merged in order. See `02-command-line.md` for details.

## Reload kitty.conf after a change

kitty reloads `kitty.conf` automatically after you save it. The `auto_reload_config` option (default `0.1`) is the number of seconds kitty waits after a change before reloading; a negative value disables automatic reloading. Automatic reloading needs `kitty.conf` to exist when kitty starts, and changing `auto_reload_config` itself by a reload has no effect.

To reload manually, press `ctrl+shift+f5` (`load_config_file`) or send `SIGUSR1` to kitty. The `load_config_file` action can also be mapped with explicit paths, `load_config_file PATH...`, which loads those files in order and replaces all current options with the result.

To see what kitty is actually using, press `ctrl+shift+f6` (`debug_config`).

## Know which options need a restart

Not every option can change while kitty is running:

- **Restart required**: `listen_on`, `linux_display_server`, `startup_session`, `update_check_interval` and `dynamic_background_opacity`. The result of changing `hide_window_decorations` by reloading is undefined.
- **New windows only**: `scrollback_lines`, `scrollback_pager_history_size` and `term` apply to windows opened after the reload.
- **Background opacity**: a new `background_opacity` value only applies on reload if `dynamic_background_opacity yes` was set when kitty started.

## Choose a font family

`font_family` sets the main font; its default is `monospace`, meaning whatever your system maps that name to. The bold, italic and bold-italic faces (`bold_font`, `italic_font`, `bold_italic_font`) default to `auto`, so kitty picks the matching styles of the main family.

A font value can be a plain family name, `auto`, or a list of `key=value` pairs. The recognised keys are `family`, `style`, `postscript_name`, `full_name`, `variable_name`, `features` and `system`. Any four-letter key is treated as an axis of a variable font, so a value such as `family="Iosevka" wght=450` selects a weight.

The easiest way to pick fonts is the interactive picker:

```
kitten choose-fonts
```

The older `kitty +list-fonts` command also lists the fonts kitty can see.

## Change the font size

`font_size` sets the size in points; the default is `11.0`. While kitty is running you can change the size with keys:

- `ctrl+shift+equal` (or `ctrl+shift+plus`, or `ctrl+shift+kp_add`) makes text 2 points larger in all windows.
- `ctrl+shift+minus` (or `ctrl+shift+kp_subtract`) makes it 2 points smaller.
- `ctrl+shift+backspace` returns to the configured size.

These keys run the `change_font_size` action; see `04-keyboard-and-mouse.md` to map your own sizes. At runtime the size can grow to at most ten times the configured `font_size`.

## Use special fonts for symbols

- `symbol_map CODEPOINTS Family Name` draws the listed characters with a specific font. Code points are written as `U+XXXX`, separated by commas, with hyphens for ranges. You can repeat the option. Example: `symbol_map U+E0A0-U+E0A3,U+E0C0 Symbols Nerd Font`.
- `narrow_symbols CODEPOINTS [cells]` forces the listed symbols to occupy the given number of cells, 1 when omitted.

## Control ligatures and font features

`disable_ligatures` decides when programming ligatures are split into separate characters. The default is `never`; `cursor` disables them only under the cursor, and `always` disables them everywhere. The `disable_ligatures_in` action changes this for the active window, all windows, or the current tab.

`font_features` switches OpenType features on or off for one face, identified by its PostScript name, for example `font_features JetBrainsMono-Regular +zero -calt`. On Linux, fontconfig's own feature settings are applied first. You can find a font's PostScript name with `fc-scan` on the font file.

## Fine-tune cell size and line metrics

`modify_font` adjusts the font's measurements. The keys are `underline_position`, `underline_thickness`, `strikethrough_position`, `strikethrough_thickness`, `cell_width`, `cell_height` and `baseline`. Add `px` for pixels or `%` for a percentage; a bare number means points.

```
modify_font cell_height 110%
modify_font baseline 1px
```

The older options `adjust_line_height`, `adjust_column_width` and `adjust_baseline` are still understood and map to `cell_height`, `cell_width` and `baseline`.

Other font-related defaults: `force_ltr no`, `box_drawing_scale 0.001, 1, 1.5, 2`, `undercurl_style thin-sparse` (also `thin-dense`, `thick-sparse`, `thick-dense`), `underline_exclusion 1`, `text_composition_strategy platform` and `text_fg_override_threshold 0`.

## Change the cursor shape and colour

- `cursor_shape` is `block` by default; the other shapes are `beam` and `underline`. Shell integration switches the cursor to a beam while you are at the prompt; add `no-cursor` to `shell_integration` to stop that.
- `cursor_shape_unfocused` (default `hollow`) is the shape in windows without focus; it also accepts `block`, `beam`, `underline` and `unchanged`.
- `cursor` sets the cursor colour, default `#cccccc`. The value `none` draws the cursor in reverse video. A colour set by the running program takes priority.
- `cursor_text_color` (default `#111111`) colours the character under the cursor; `background` uses the cell's background colour. It has no effect when `cursor` is `none`.
- `cursor_beam_thickness 1.5` and `cursor_underline_thickness 2.0` are in points.

## Make the cursor blink, stop blinking, or leave a trail

- `cursor_blink_interval` (default `-1`) is the blink period in seconds. `0` stops blinking; a negative value uses the system's setting. You may add easing functions, as in `cursor_blink_interval 0.6 ease-in-out`. The same interval drives blinking text.
- `cursor_stop_blinking_after` (default `15.0`) stops the blink after that many seconds without input; `0` keeps it blinking forever.
- `cursor_trail` (default `0`) enables an animated trail behind a moving cursor when set above zero (in milliseconds). Related settings are `cursor_trail_decay 0.1 0.4`, `cursor_trail_start_threshold 2` and `cursor_trail_color none`.

**In Kilix:** the Kilix-only option `software_mouse_cursor` (default `block`, also `pointer` or `none`) draws the mouse pointer inside the terminal grid; `none` keeps the ordinary system pointer.

## Keep more scrollback history

- `scrollback_lines` (default `2000`) is the number of lines each window remembers. A negative value makes it effectively unlimited. Memory is allocated only as lines are used, but very large values can slow kitty down.
- `scrollback_pager_history_size` (default `0`, in megabytes) adds a separate, larger buffer that is only used when the scrollback is shown in the pager. Roughly 10,000 lines fit in one megabyte; the maximum is 4 GB; zero or less turns it off.
- `scrollback_fill_enlarged_window` (default `no`) decides whether lines from the scrollback fill the space when a window grows.

## Change the scrollback pager

`ctrl+shift+h` shows kitty's scrollback in a pager. The `scrollback_pager` option chooses the program, by default:

```
scrollback_pager less --chop-long-lines --RAW-CONTROL-CHARS +INPUT_LINE_NUMBER
```

kitty replaces `INPUT_LINE_NUMBER`, `CURSOR_LINE` and `CURSOR_COLUMN` in this command before running it. Whatever pager you use must understand ANSI colour escape codes.

## Configure the scrollbar

`scrollbar` controls when kitty's scrollbar is visible: `scrolled` (the default, while scrolled back), `always`, `never`, `hovered`, or `scrolled-and-hovered`. Many details can be tuned; the defaults are `scrollbar_interactive yes`, `scrollbar_jump_on_click yes`, `scrollbar_width 0.5`, `scrollbar_hover_width 1`, `scrollbar_handle_opacity 0.5`, `scrollbar_radius 0.3`, `scrollbar_gap 0.1`, `scrollbar_min_handle_height 1`, `scrollbar_hitbox_expansion 0.25`, `scrollbar_track_opacity 0`, `scrollbar_track_hover_opacity 0.1`, and `foreground` for both `scrollbar_handle_color` and `scrollbar_track_color`. The older `scrollback_indicator_opacity` is replaced by `scrollbar`.

`progress_bar` (default `top`; also `left`, `right`, `bottom`, `hidden`) chooses where a program's reported progress is drawn.

## Adjust mouse-wheel scrolling speed

- `wheel_scroll_multiplier` (default `5.0`) multiplies scrolling for ordinary, low-precision wheels. A negative value reverses the direction.
- `wheel_scroll_min_lines` (default `1`) is the smallest number of lines one wheel step scrolls.
- `touch_scroll_multiplier` (default `1.0`) applies to touchpads and other high-precision devices.
- `pixel_scroll` defaults to `yes` and `momentum_scroll` to `0.96`.

## Hide the mouse pointer while typing

`mouse_hide_wait` (default `3.0` on Linux) hides the mouse pointer after that many seconds of no mouse movement. `0` never hides it; a negative value hides it as soon as you type. A longer form takes four values: hide delay, unhide delay, unhide movement threshold, and whether scrolling unhides.

Pointer shapes are set by `default_pointer_shape beam`, `pointer_shape_when_grabbed arrow` and `pointer_shape_when_dragging beam crosshair`. `drag_threshold 5` sets how far the mouse must move before a press becomes a drag.

## Control how URLs are detected and opened

- `detect_urls yes` finds URLs in the text. Even with `detect_urls no`, URLs can still be clicked.
- `url_prefixes` lists the schemes that count as URLs; the default is `file ftp ftps gemini git gopher http https irc ircs kitty mailto news sftp ssh`.
- `open_url_with default` opens URLs using kitty's open-actions rules and then `xdg-open` on Linux. Replace `default` with a program name to use that instead.
- `url_color #0087bd` and `url_style curly` (also `none`, `straight`, `double`, `dotted`, `dashed`) set the colour and underline style kitty uses for URLs.
- `url_excluded_characters` (empty by default), `show_hyperlink_targets never` and `underline_hyperlinks hover` (also `always`, `never`) fine-tune link handling.

## Copy text automatically when selecting

`copy_on_select` defaults to `no`. Set it to `clipboard` to copy every selection to the clipboard. Any other word, such as `copy_on_select sel1`, copies into a private named buffer that you paste with `paste_from_buffer sel1`.

Related options: `clear_selection_on_clipboard_loss no`; `strip_trailing_spaces never` (or `smart`, which strips except in rectangle selections, or `always`); `select_by_word_characters @-./_~?&=%+#`, the characters besides letters and digits that count as part of a word on double-click; and `select_by_word_characters_forward`, empty by default.

## Make pasting safer

`paste_actions` (default `quote-urls-at-prompt,confirm`) lists what kitty does to text before pasting it. The choices are:

- `quote-urls-at-prompt`: quote a pasted URL when you are at a shell prompt.
- `replace-dangerous-control-codes`: replace dangerous control codes in the pasted text.
- `replace-newline`: replace newline characters in the pasted text.
- `confirm`: ask for confirmation before pasting.
- `confirm-if-large`: ask before pasting more than 16 KB.
- `filter`: run a `filter_paste()` function from `paste-actions.py` in the configuration directory.
- `no-op`: do nothing special.

## Tune clicks and focus

`click_interval` (default `-1.0`) is the maximum time between clicks for a double or triple click; a negative value uses the system setting, falling back to 0.5 seconds. `focus_follows_mouse` (default `no`) moves focus to the kitty window under the pointer when `yes`, or only during drag and drop when `drop`. `clear_all_mouse_actions no` keeps the default mouse bindings; `mouse_map` lines are explained in `04-keyboard-and-mouse.md`.

## Tune rendering performance

- `repaint_delay` (default `10` ms) is the minimum gap between screen updates, about 100 frames per second.
- `input_delay` defaults to `3` ms.
- `sync_to_monitor yes` avoids tearing by matching the monitor's refresh rate. If typing feels sluggish, try `sync_to_monitor no`.

## Configure the bell

- `enable_audio_bell yes` plays a sound on the bell. `bell_path` (default `none`) chooses a sound file, relative to the configuration directory; on Linux WAV and OGA files play through libcanberra. `linux_bell_theme __custom` names the sound theme.
- `visual_bell_duration 0.0` flashes the window for that many seconds; `0` turns the flash off. `visual_bell_color none` uses the selection background colour.
- `window_alert_on_bell yes` asks the desktop to flag the OS window, for example by flashing its taskbar entry.
- `bell_on_tab "🔔 "` puts that text on the tab of an unfocused window that rang.
- `command_on_bell none` can run a command instead; it sees the variable `KITTY_CHILD_CMDLINE`.

## Set the initial OS window size

`remember_window_size yes` makes kitty reopen at its last size. When it is `no`, `initial_window_width 640` and `initial_window_height 400` apply; the numbers are pixels, or cells if you add `c`, as in `initial_window_width 100c`. `remember_window_position` defaults to `no`.

## Add borders, margins and padding around kitty windows

- `window_border_width 0.5pt` sets the border between kitty windows (units `pt` or `px`). Borders only appear when a tab shows more than one window. `draw_minimal_borders yes` is the default, though a non-zero margin overrides it; `draw_window_borders_for_single_window no` keeps a lone window borderless.
- `active_border_color #00ff00` marks the focused window (`none` disables it), `inactive_border_color #cccccc` the others, and `bell_border_color #ff5a00` a window that rang its bell.
- `window_margin_width 0` is space outside the border; `window_padding_width 0` is space between the text and the border. Both take one to four values: one for all sides, two for vertical then horizontal, three for top, horizontal and bottom, or four for top, right, bottom and left.
- `single_window_margin_width -1` and `single_window_padding_width -1` apply when only one window is visible; negative means "use the normal value".
- `placement_strategy center` can also be `top-left`, `top`, `top-right`, `left`, `right`, `bottom-left`, `bottom` or `bottom-right`.
- `inactive_text_alpha 1.0` makes text in unfocused windows fainter when set below 1. The range is -1 to 1; a negative value fades text only if the tab shows several windows.

## Hide window decorations and add title bars

`hide_window_decorations no` keeps the desktop's title bar; `yes` removes decorations, and on Wayland `titlebar-only` removes just the title bar. The older names `x11_hide_window_decorations` and `macos_hide_titlebar` are replaced by this option.

kitty 0.48 can also draw title bars on individual kitty windows: `window_title_bar top` (or `bottom`), shown according to `window_title_bar_min_windows 0` (0 never, 1 always, N when at least N windows are visible). Their text comes from `window_title_template`, alignment from `window_title_bar_align center`, and colours from the `window_title_bar_active_*` and `window_title_bar_inactive_*` options.

## Ask before closing windows with running programs

`confirm_os_window_close` (default `-1`) asks for confirmation when you close an OS window, a tab, or quit kitty while at least that many kitty windows are open. `0` never asks. A negative value, together with shell integration, does not count windows that are just sitting at a prompt. Append `count-background` to also count background jobs.

Other window options: `enabled_layouts *` (all layouts; see `05-tabs-windows-layouts.md`), `window_resize_step_cells 2`, `window_resize_step_lines 2`, `window_drag_tolerance 2`, `resize_debounce_time 0.1 0.5`, `resize_in_steps no`, `visual_window_select_characters`, and a background logo with `window_logo_path none`, `window_logo_position bottom-right`, `window_logo_alpha 0.5` and `window_logo_scale 0`.

## Move and style the tab bar

- `tab_bar_edge bottom` puts the tab bar at the bottom; `top`, `left` and `right` also work.
- `tab_bar_style fade` is the default look. Alternatives are `slant`, `separator`, `powerline`, `custom` (you write a `draw_tab` function in `tab_bar.py` in the configuration directory) and `hidden` (no tab bar; use the `select_tab` action to switch tabs).
- `tab_bar_min_tabs 2` shows the tab bar only once there are at least two tabs. Set it to `1` to always show it.
- `tab_bar_align start` (also `center`, `end`) aligns the tabs.
- `tab_powerline_style angled` (also `slanted`, `round`), `tab_separator " ┇"` and `tab_fade 0.25 0.5 0.75 1` tune individual styles.
- `tab_bar_show_new_tab_button no`, `tab_bar_margin_width 0.0` and `tab_bar_margin_height 0.0 0.0` control extras and spacing.
- Colours: `active_tab_foreground #000`, `active_tab_background #eee`, `active_tab_font_style bold-italic`, `inactive_tab_foreground #444`, `inactive_tab_background #999`, `inactive_tab_font_style normal`, `tab_bar_background none` and `tab_bar_margin_color none`.

## Change what a tab title shows

`tab_title_template` is a Python format string that builds each tab's label. The default is:

```
tab_title_template "{fmt.fg.red}{bell_symbol}{activity_symbol}{secure_input_symbol}{fmt.fg.tab}{tab.last_focused_progress_percent}{title}"
```

A simple numbered variant would be `tab_title_template "{index} {title}"`. Available fields include `title`, `index`, `sup.index` (superscript number), `layout_name`, `session_name`, `active_session_name`, `num_windows`, `num_window_groups`, `keyboard_mode`, `max_title_length`, `bell_symbol`, `activity_symbol`, `secure_input_symbol`, `tab.active_wd`, `tab.active_oldest_wd`, `tab.active_exe`, `tab.active_oldest_exe`, `tab.progress_percent`, `tab.last_focused_progress_percent`, `tab.children_mem_usage` and `custom`. Python expressions such as `{layout_name[:3]}` are allowed.

Formatting codes: `{fmt.fg.red}` or `{fmt.fg.color4}` change the text colour, `{fmt.bg._2e3440}` sets a background by hex value, `{fmt.fg.tab}` and `{fmt.bg.tab}` return to the tab's normal colours, and `{fmt.bold}`, `{fmt.nobold}`, `{fmt.italic}`, `{fmt.noitalic}` toggle styles. If your template omits `bell_symbol` or `activity_symbol`, kitty adds them at the front. `active_tab_title_template none` means the active tab uses the same template. `tab_title_max_length 0` means no length limit, and `tab_activity_symbol none` sets no activity marker.

## Choose which tab kitty shows after closing one

`tab_switch_strategy previous` returns to the previously active tab when you close the current one. The alternatives are `left`, `right` and `last`. `tab_bar_filter` (empty by default) takes a search expression that limits which tabs appear in the tab bar and which tabs tab-navigation shortcuts visit; the active tab is always shown.

## Change the terminal colours

The basic colours are `foreground #dddddd` and `background #000000`. Selections use `selection_foreground #000000` and `selection_background #fffacd`; setting both to `none` gives reverse-video selections.

The sixteen standard colours default to:

| Colour | Normal | Bright |
|---|---|---|
| Black | `color0 #000000` | `color8 #767676` |
| Red | `color1 #cc0403` | `color9 #f2201f` |
| Green | `color2 #19cb00` | `color10 #23fd00` |
| Yellow | `color3 #cecb00` | `color11 #fffd00` |
| Blue | `color4 #0d73cc` | `color12 #1a8fff` |
| Magenta | `color5 #cb1ed1` | `color13 #fd28ff` |
| Cyan | `color6 #0dcdcd` | `color14 #14ffff` |
| White | `color7 #dddddd` | `color15 #ffffff` |

`color16` to `color255` can be set too; by default they follow the standard 256-colour palette. `palette_generate` (default `fixed`) decides how unset entries are filled: `fixed` uses the traditional values, `semantic` derives them from your first 16 colours in a way that reads better on light themes, and `legacy` also derives them but stays closer to the fixed values. The colours for marks are `mark1_foreground black` / `mark1_background #98d3cb`, `mark2_background #f2dcd3` and `mark3_background #f274bc` (with black foregrounds).

## Pick a colour theme

Run `kitten themes` to browse and preview themes. When you choose one, it writes `current-theme.conf` in the configuration directory and adds `include current-theme.conf` to `kitty.conf`. Put any colour changes of your own after that include line.

To follow the desktop's light or dark preference automatically, create `dark-theme.auto.conf`, `light-theme.auto.conf` and `no-preference-theme.auto.conf` in the configuration directory. kitty loads the one matching the current preference. These files override every other colour setting, even `-o` on the command line, and the background image settings too.

At runtime, the `set_colors` action and `launch --color` change colours for particular windows.

## Make the background transparent

`background_opacity` (default `1.0`) makes the background see-through when lowered towards 0; it needs a compositor, affects only cells that use the default background colour, costs some performance, and does not apply to a background image. To change opacity while kitty runs (with the `ctrl+shift+a` key sequences), you must start kitty with `dynamic_background_opacity yes`. `background_blur 0` and `transparent_background_colors` (empty) refine the effect. The default `dim_opacity` is `0.4`.

## Set a background image

`background_image` (default `none`) accepts PNG, JPEG, WEBP, TIFF, GIF or BMP files and may be a glob pattern. `background_image_layout tiled` can also be `mirror-tiled`, `scaled`, `clamped`, `centered` or `cscaled`. Related options are `background_image_linear no`, `background_tint 0.0` and `background_tint_gaps 1.0`.

## Choose the shell and editor

`shell .` starts your `$SHELL`, or your login shell if that is unset; give a program path to run something else. Environment variables in the value are expanded. `editor .` picks the editor for `kitty.conf` (see `01-getting-started.md`). `close_on_child_death` defaults to `no`.

## Set environment variables for programs in kitty

`env NAME=VALUE` sets a variable for every program kitty starts. You can repeat it. `env NAME=` sets an empty value, and `env NAME` on its own removes the variable. Values may refer to other variables. To copy variables from your login shell, use `env read_from_shell=PATH LANG LC_*`.

## Enable remote control

`allow_remote_control` (default `no`) lets programs control kitty through `kitten @`. The values are:

- `no`: off.
- `yes`: allowed.
- `socket`: always allowed over a socket; from a kitty window only with a password.
- `socket-only`: only over a socket; programs in kitty windows are refused.
- `password`: every request must supply a password.

`remote_control_password` (repeatable) pairs a password with the actions it may run. `listen_on none` sets a socket address such as `unix:/tmp/kitty-{kitty_pid}`; if the value does not contain `{kitty_pid}`, kitty appends `-PID`. A TCP address always uses a random port. `listen_on` requires a restart to change.

## Use other advanced options

- `startup_session none` opens a session file at every start (relative paths are taken from the configuration directory). It is ignored when a program is given on the command line, and `--session=none` suppresses it.
- `shell_integration enabled` turns on shell integration. Use `disabled`, or a list of switches from `no-rc`, `no-cursor`, `no-title`, `no-cwd`, `no-prompt-mark`, `no-complete` and `no-sudo`.
- `notify_on_cmd_finish never` can notify you when a long command finishes: set when (`unfocused`, `invisible`, `always`), an optional minimum duration (default 5 seconds) and an action (`notify`, `bell`, `notify-bell` or `command CMD`, where `%c` is the command line and `%s` the exit status). Example: `notify_on_cmd_finish unfocused 20 notify`.
- `clipboard_control` sets what programs may do with the clipboard; the default is `write-clipboard write-primary read-clipboard-ask read-primary-ask`. `clipboard_max_size 512` caps program-written clipboard data in megabytes.
- `allow_hyperlinks yes`, `allow_cloning ask`, `clone_source_strategies venv,conda,env_var,path`, `file_transfer_confirmation_bypass` (empty), `update_check_interval 24` (hours; official binaries only).
- `term xterm-kitty` is the `TERM` value given to programs; changing it causes problems. `terminfo_type path` (also `direct`, `none`) and `forward_stdio no`.
- `watcher`, `exe_search_path`, `filter_notification` and `menu_map` can each be repeated.

## Set Linux display options

- `linux_display_server auto` picks Wayland or X11; force one with `wayland` or `x11`. This needs a restart.
- `wayland_titlebar_color system` colours the title bar drawn by kitty on compositors that expect the client to draw it (for example GNOME). Use `background` to match the terminal background, or give a colour.
- `wayland_enable_ime yes` enables input-method support on Wayland.

## Configure keyboard shortcut options

`kitty_mod ctrl+shift` is the modifier used in almost all default shortcuts. `clear_all_shortcuts no`, `map_timeout 0.0`, `action_alias` and the older `kitten_alias` also belong to this group. The details are in `04-keyboard-and-mouse.md`.

## See also

- `01-getting-started.md` - kitty's building blocks and first steps
- `02-command-line.md` - starting kitty and its command-line options
- `04-keyboard-and-mouse.md` - shortcuts and mouse bindings
- `05-tabs-windows-layouts.md` - managing tabs, windows and layouts
- `06-launch-and-sessions.md` - the `launch` action and session files
