# Tabs, windows and layouts in kitty

kitty 0.48.2, as bundled in Kilix on Linux, arranges your terminals in three levels: OS windows contain tabs, and tabs contain kitty windows (panes). Each tab has its own layout that tiles its kitty windows automatically. This guide shows how to open, close, switch, move, rename and detach tabs and kitty windows, how to resize kitty windows with the keyboard or mouse, how to choose and control layouts, and what each of the seven layouts does, including the options each layout accepts. Default keys assume `kitty_mod` is `ctrl+shift`.

## Understand how kitty arranges terminals

An OS window is the window your desktop manages. Inside it are one or more tabs, and each tab holds one or more kitty windows, each running its own terminal. The kitty windows in a tab are tiled automatically according to that tab's layout, so different tabs can use different layouts.

Overlay windows, such as the scrollback pager, sit on top of one kitty window. They are skipped when you move between windows with next and previous.

## Open a new tab

Press `ctrl+shift+t` (`new_tab`) to open a new tab in the current OS window. To open a tab that starts in the same directory as the current window, map `new_tab_with_cwd`, which has no default key:

```
map ctrl+alt+t new_tab_with_cwd
```

A tab opened with `new_tab_with_cwd` also joins the active session, if there is one. You can also double-click an empty part of the tab bar to open a new tab.

## Close a tab

Press `ctrl+shift+q` (`close_tab`) to close the current tab and every kitty window in it. `close_other_tabs_in_os_window` closes every tab except the current one.

After a tab closes, kitty's `tab_switch_strategy` option picks the next tab to show. The default `previous` returns to the tab you used before; `left`, `right` and `last` are the alternatives.

## Switch between tabs

- `ctrl+shift+right` or `ctrl+tab` (`next_tab`) goes to the tab on the right.
- `ctrl+shift+left` or `ctrl+shift+tab` (`previous_tab`) goes to the tab on the left.
- `goto_tab N` jumps to tab number N, counting from 1. `goto_tab -1` returns to the previously active tab, and smaller numbers go further back; `0` also refers to earlier tabs.
- `select_tab` shows an interactive list to choose a tab from. It is especially useful with `tab_bar_style hidden`.
- `toggle_tab EXPR` jumps to the tab matching a search expression, or back to the tab you came from if you are already there. It only searches the current OS window.

```
map alt+1 goto_tab 1
map alt+2 goto_tab 2
map f4 toggle_tab title:notes
```

## Reorder tabs

Press `ctrl+shift+.` (`move_tab_forward`) or `ctrl+shift+,` (`move_tab_backward`) to shift the current tab along the tab bar. With the mouse, drag a tab to a new position. Dropping a tab onto another OS window's tab bar moves it there, and dropping it outside any kitty window gives it its own new OS window.

## Rename a tab

Press `ctrl+shift+alt+t` (`set_tab_title`) to type a new title for the current tab, or double-click the tab. When you map `set_tab_title` yourself, an argument sets the title directly: `set_tab_title Build` names the tab "Build", `set_tab_title ""` goes back to the automatic title, and `set_tab_title " "` opens the prompt with an empty field.

## Move a tab to its own OS window

`detach_tab` moves the current tab into a new OS window, which is the default `new` behaviour. `detach_tab ask` lets you choose the destination instead.

## Show a new-tab button

By default kitty does not show a permanent "+" button; `tab_bar_show_new_tab_button no` makes it appear only while you drag a kitty window, as a place to drop that window into a new tab. Set `tab_bar_show_new_tab_button yes` to keep the button visible all the time.

## Open a new kitty window in a tab

Press `ctrl+shift+enter` (`new_window`) to add a kitty window to the current tab. Its position depends on the tab's layout. To start it in the current window's directory, map `new_window_with_cwd`:

```
map ctrl+alt+enter new_window_with_cwd
```

For precise control over where a new window goes and what runs in it, use the `launch` action described in `06-launch-and-sessions.md`.

## Open a new OS window

Press `ctrl+shift+n` (`new_os_window`) for a new OS window. `new_os_window_with_cwd` does the same, starting in the current directory. `toggle_fullscreen` (`ctrl+shift+f11`) and `toggle_maximized` (`ctrl+shift+f10`) change the current OS window's state.

## Close kitty windows and OS windows

- `ctrl+shift+w` (`close_window`) closes the focused kitty window.
- `close_window_with_confirmation` asks before closing the focused kitty window. It accepts an optional `ignore-shell` argument.
- `close_other_windows_in_tab` keeps only the focused kitty window in the tab.
- `close_os_window` closes the whole OS window (no default key on Linux), `close_other_os_windows` closes every other OS window, and `quit` exits kitty.

## Move focus between kitty windows

- `ctrl+shift+]` (`next_window`) and `ctrl+shift+[` (`previous_window`) move focus in order.
- `ctrl+shift+1` to `ctrl+shift+9` focus the first to ninth window and `ctrl+shift+0` the tenth. Windows are numbered clockwise starting at the top left.
- `neighboring_window left`, `right`, `up` or `down` (also `top` and `bottom`) focuses the window next to the current one in that direction.
- `nth_window N` focuses a window by zero-based number; a negative number goes to previously active windows, for instance `nth_window -1`. A number past the end focuses the last window.
- `nth_os_window N` focuses an OS window by number, counting from 1; negative numbers go to previously active OS windows and `0` refocuses the current one, if the window manager allows.

## Pick a window by its label

Press `ctrl+shift+f7` (`focus_visible_window`) and kitty puts a label on every visible kitty window; press a label's character to focus that window. The labels come from the `visual_window_select_characters` option, which defaults to the digits followed by the capital letters. Press `ctrl+shift+f8` (`swap_with_window`) to pick a window the same way and swap places with it.

## Rearrange kitty windows in a tab

- `ctrl+shift+f` (`move_window_forward`) and `ctrl+shift+b` (`move_window_backward`) move the focused window one place along the layout order.
- ``ctrl+shift+` `` (`move_window_to_top`) moves it to the top of the window order.
- `move_window left`, `right`, `up` or `down` (also `top`, `bottom`, or a number) moves it in a direction.

When per-window title bars are showing, you can also drag a title bar to reorder windows. `window_title_bar top` (or `bottom`) sets where the bars go, and `window_title_bar_min_windows` sets when they appear: `0` never, `1` always, or a number N to show them once at least N windows are visible. The `toggle_window_title_bars` action reveals hidden title bars temporarily so you can drag one.

## Move a kitty window to another tab or OS window

`detach_window` moves the focused kitty window somewhere else. Without an argument it goes into a new OS window. Other targets:

| Argument | Destination |
|---|---|
| `new` | A new OS window (the default) |
| `new-tab` | A new tab |
| `new-tab-left`, `new-tab-right` | A new tab to the left or right of the current one |
| `tab-prev` | The previously active tab |
| `tab-left`, `tab-right` | The neighbouring tab on that side |
| `ask` | Choose interactively |

```
map ctrl+alt+d detach_window new-tab
```

## Rename a kitty window

`set_window_title` works like `set_tab_title`: with a title argument it sets that title, with `""` it goes back to the title set by the program, and with `" "` it prompts with an empty field.

## Resize kitty windows with the mouse

Drag the border between two kitty windows to resize them. The area where a border can be grabbed is set by `window_drag_tolerance` (default `2` points); a large negative value such as `-200` turns border dragging off.

Resizing changes a row, column or slot of the layout, so more than one kitty window may change size at once.

## Resize kitty windows with the keyboard

Press `ctrl+shift+r` (`start_resizing_window`) to enter resize mode, then use:

| Key | Effect |
|---|---|
| `w` | Wider |
| `n` | Narrower |
| `t` | Taller |
| `s` | Shorter |
| `r` | Reset sizes |
| `Esc` or `q` | Leave resize mode |

Hold `ctrl` with a key to take a double step. Each step is `window_resize_step_cells` columns (default 2) horizontally or `window_resize_step_lines` lines (default 2) vertically.

To resize without the interactive mode, map `resize_window` with `wider`, `narrower`, `taller` or `shorter` and an optional count (default 1), or `resize_window reset`. `reset_window_sizes` undoes every manual resize. Only directions that make sense for the current layout have an effect; in `tall`, for example, only the width of the main column can change.

```
map ctrl+alt+right resize_window wider 3
map ctrl+alt+left resize_window narrower 3
```

## Choose which layouts are available

`enabled_layouts` lists the layouts a tab can cycle through. The default, `*`, enables all seven in alphabetical order: `fat`, `grid`, `horizontal`, `splits`, `stack`, `tall`, `vertical`. The first layout in the list is the one new tabs start with, which is why kitty starts in `fat` unless you change this.

```
enabled_layouts splits,stack,tall
```

A layout name can carry options after a colon, written `name:key=value;key=value`, as in `enabled_layouts tall:bias=65,stack`.

## Switch layouts

- `ctrl+shift+l` (`next_layout`) moves to the next enabled layout. Mapped with a number, `next_layout N` jumps by that many.
- `last_used_layout` returns to the layout used before.
- `goto_layout NAME` switches to a named layout. If the same layout appears more than once with different options, give the full definition or a prefix that is unique.
- `toggle_layout NAME` switches to NAME, or back again if you are already in it.

A popular use of `toggle_layout` is a zoom key that makes the focused window fill the tab, then restores the previous layout:

```
map ctrl+shift+z toggle_layout stack
```

(That example replaces the default `ctrl+shift+z` prompt-jump key; pick another key if you use that.) The `scrollback_fill_enlarged_window` option affects how an enlarged window is filled. `layout_action` sends layout-specific commands, described with each layout below.

## The stack layout

The `stack` layout shows one kitty window filling the whole tab; the other windows are hidden behind it. Switch between them with the normal window focus keys. It has no options.

## The tall layout

The `tall` layout puts a main column on the left, running the full height of the tab, and stacks the remaining kitty windows on the right. Options:

- `bias` (10 to 90, default 50): the percentage of the width given to the main column.
- `full_size` (default 1, limited to 1-100): how many windows share the main column.
- `mirrored` (default false): when true, the main column is on the right.

```
enabled_layouts tall:bias=60;full_size=1;mirrored=false
```

Layout actions for `tall`: `layout_action increase_num_full_size_windows`, `layout_action decrease_num_full_size_windows`, `layout_action mirror` (with `toggle`, `true` or `false`; toggle is the default), and `layout_action bias 70 50 30`, which cycles through the listed widths. With a single value, `bias` toggles between that value and 50.

## The fat layout

The `fat` layout is `tall` turned on its side: main window or windows form a full-width row at the top, and the others sit side by side underneath. It accepts the same options and layout actions as `tall`; with `mirrored` true, the main row is at the bottom.

## The grid, horizontal and vertical layouts

- `grid` arranges kitty windows in a balanced grid of equal sizes; only the last column may differ.
- `horizontal` places all kitty windows side by side in one row.
- `vertical` stacks all kitty windows top to bottom in one column.

None of these three layouts has options.

## The splits layout

The `splits` layout lets you build any arrangement by repeatedly splitting windows horizontally or vertically, forming a tree of splits. New windows are placed with the `launch` action's `--location` option:

- `vsplit` puts the new window beside the current one, on the right; `vsplit-before` puts it on the left.
- `hsplit` puts the new window below the current one; `hsplit-before` puts it above.
- `split` chooses automatically based on the current window's shape.

```
map f5 launch --location=hsplit --cwd=current
map f6 launch --location=vsplit --cwd=current
```

Use `neighboring_window DIR` to move focus and `move_window DIR` to move windows between splits.

## Configure the splits layout

The `splits` layout accepts two options:

- `split_axis` (default `horizontal`) decides where a new window goes when no `--location` is given: `horizontal` behaves like `vsplit`, `vertical` like `hsplit`, and `auto` like `split`.
- `equalize_on_window_close` (default false) evens out the remaining splits when a window closes. Write it as `enabled_layouts splits:equalize_on_window_close=true`. Some upstream material spells this `equalize_on_close`, but kitty 0.48.2 only reads `equalize_on_window_close`.

Layout actions for `splits`:

- `layout_action rotate` turns the current split by 90 degrees; `rotate 180` swaps the two sides, and `rotate 270` rotates and swaps.
- `layout_action move_to_screen_edge left` (or `right`, `top`, `bottom`) moves the window to that edge of the tab.
- `layout_action bias 70` gives the focused window 70% of its parent split (default 50).
- `layout_action maximize horizontal` or `vertical` makes the window fill one axis; running it again restores it.
- `layout_action equalize` makes the splits equal.

## Size a new window with launch --bias

When you open a window with `launch --bias N`, the number means something different in each layout:

- `splits`: the percentage (0 to 100) of the original window's space that the new window takes.
- `vertical` and `horizontal`: a value from -90 to 90, roughly the percentage of the OS window added to or taken from the new window's normal size.
- `tall` and `fat`: for the first window in a column (a row, for `fat`), the percentage split between columns; for later windows, it adds or subtracts size like `vertical`.
- `grid`: for the first window in a column it sets the column width; for later windows it sets the row height.

## Adjust borders and spacing between kitty windows

kitty draws borders only if two or more kitty windows are on screen. `window_border_width` (default `0.5pt`) sets their thickness, `draw_minimal_borders yes` keeps them minimal, and the colours come from `active_border_color #00ff00`, `inactive_border_color #cccccc` and `bell_border_color #ff5a00`.

To give one window extra space at launch, use `launch --spacing`, for example `launch --spacing padding=8` or `launch --spacing margin-h=20`. The remote-control command `set-spacing` changes spacing on a running window. `03-configuration.md` covers the global margin and padding options.

## See also

- `01-getting-started.md` - kitty's building blocks and first steps
- `02-command-line.md` - starting kitty and its command-line options
- `03-configuration.md` - the `kitty.conf` file and its options
- `04-keyboard-and-mouse.md` - shortcuts and mouse bindings
- `06-launch-and-sessions.md` - the `launch` action and session files
