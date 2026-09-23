# kitty user guide (MIT)

Task-oriented documentation for the kitty terminal 0.48.2, as shipped inside
Kilix on Linux. Written independently under the MIT licence (see LICENSE).

kitty itself and its upstream documentation are GPLv3 and are **not** included
or quoted here. These pages were produced by a clean-room process: one group
extracted bare facts (command names, option names, defaults and behaviour)
from the upstream sources, and a separate group, who never read those
sources, wrote this text from the facts alone. An automated scan found no
8-word run of text shared with the upstream documentation or option
descriptions, and every option, action and remote-control command named here
exists in kitty 0.48.2.

| Page | What it covers |
|---|---|
| [Getting started with kitty](01-getting-started.md) | kitty is a terminal emulator that draws its whole interface on the graphics card. This guide covers kitty 0.48.2, the version bundled inside the Kilix terminal on Linux.… |
| [Starting kitty from the command line](02-command-line.md) | This guide explains how to start kitty 0.48.2 (as bundled in Kilix on Linux) from a shell or launcher, and which command-line options are worth knowing. It covers… |
| [Configuring kitty with kitty.conf](03-configuration.md) | kitty 0.48.2, as shipped in Kilix on Linux, is configured through one plain-text file, `kitty.conf`. This guide explains the file's syntax, how to split a configuration… |
| [Keyboard shortcuts and mouse bindings in kitty](04-keyboard-and-mouse.md) | This guide explains how keyboard shortcuts and mouse bindings work in kitty 0.48.2 as bundled in Kilix on Linux. It covers the `map` line and how to write key names, how… |
| [Tabs, windows and layouts in kitty](05-tabs-windows-layouts.md) | kitty 0.48.2, as bundled in Kilix on Linux, arranges your terminals in three levels: OS windows contain tabs, and tabs contain kitty windows (panes). Each tab has its… |
| [The launch action and session files in kitty](06-launch-and-sessions.md) | This guide covers two related features of kitty 0.48.2 as bundled in Kilix on Linux. The `launch` action opens a new kitty window, tab, OS window, overlay or background… |
| [Remote control: scripting kitty with `kitten @`](07-remote-control.md) | kitty can be driven from the outside. A program or script can ask a running kitty to open windows and tabs, send keystrokes, read what is on screen, change colors and… |
| [Shell integration: prompts, command output and working directories](08-shell-integration.md) | Shell integration is a small piece of shell code that kitty loads into bash, zsh or fish when a new shell starts. That code tells kitty where each prompt begins, when a… |
| [Scrollback, searching, clearing and marks](09-scrollback-search-marks.md) | Everything that scrolls off the top of a kitty window goes into the scrollback, a history buffer you can scroll back through with the keyboard, the mouse or the… |
| [Copy, paste, selections, URLs and hyperlinks](10-clipboard-and-links.md) | This page is about moving text in and out of kitty and following links. It covers the default copy and paste keys, the primary selection, named private buffers, the… |
| [Kittens: kitty's built-in helper programs](11-kittens.md) | Kittens are small programs that come with kitty and use its special features: showing images, comparing files side by side, picking text on screen with the keyboard,… |
| [Troubleshooting kitty](12-troubleshooting.md) | This page collects common kitty problems on Linux, each written as the problem you see, why it happens, and how to fix it. It starts with the diagnostic tools built into… |
