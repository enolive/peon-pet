# Peon Pet

![2b sleeping](docs/intro.png)

A friendly companion to [PeonPing](https://www.peonping.com/). Will read its state and animate it in different manners.

<video src="https://raw.githubusercontent.com/enolive/peon-pet/main/docs/demo.webm" autoplay loop muted playsinline width="400"></video>

## Features

- **Watch Mode**: Automatically updates the pet's state based on PeonPing's activity.
- **Customizable Character**: Choose between different character designs (`orc` and `2b`). Or create and include your
  own in `src/peon_pet/config.py`.
- **Tray Control**: Show/Hide pet or quit the program.
- **Draggable Window**: Pet is in your way? No problem, drag it somewhere else.
- **Support for multiple sessions**: Pet displays the number of active sessions in a badge.
- **Agent agnostic**: Pet only relies on an installed and working PeonPing. Use the agents you like!

> [!NOTE]
> Multiple-session support is best effort only. Peon Ping does not keep track of this, so we
> have no agent-agnostic way to reliably identify them all.
> If you start the pet, it will try to detect any already started sessions, but that might not be always accurate.
> It will also try to catch up on any activity.
> If you believe the number of active sessions is totally of, you can reset them via the Tray Control.

## Installation

Requirements:

* [uv]([https://github.com/uvloop/uvloop](https://docs.astral.sh/uv/)): Package manager
* [Python 3](https://www.python.org/): uv will try to bootstrap it if not present

```bash
./install.sh
```

Builds the wheel, installs the `peon-pet` command via `uv tool`, and drops the desktop entry + icon so it shows up in
your app menu.

## Usage

```bash
# starts the pet in the watch mode. Will read its state from `~/.claude/hooks/peon-ping/.state.json'
peon-pet --watch
# starts the pet in the watch mode with a custom state path
peon-pet --watch path/to/.state.json
# list all available options
peon-pet --help
```

## Configuration

Peon pet creates a `config.json` inside your config directory, usually `~/.config/peon-pet`.

```
{
  "window": {
    "x": 2282,
    "y": 1144
  },
  "atlas": "2b",
  "loops": 3
}
```

- **`window`**: current position of the window on your screen. Defaults to bottom left on your primary screen.
- **`atlas`**: which character to use. Defaults to `2b`. There is also `orc` available.
- **`loops`**: how many times to loop an animation. Defaults to `3`.

> [!NOTE]
> 'typing' and 'sleeping' loop forever.

## Available animations

| Animation | Description                                  |
|-----------|----------------------------------------------|
| sleeping  | nothing to do                                |
| waking    | session started, getting up                  |
| typing    | doing some work                              |
| alarmed   | something happened that needs your attention |
| celebrate | work was finished                            |
| annoyed   | something went wrong                         |

## Events

Refer to `peon-pet --list-events`. It maps Claude-style Events to animations.

## Other stuff from the author that is not totally unrelated

- adapter to PeonPing for pi https://github.com/enolive/pi-peon-adapter
- OpenPeon sound pack https://openpeon.com/packs/nier-2b

For more funny stuff, check out my main GitHub Repo: https://github.com/enolive

## Inspiration

Original idea from the PeonPing project: https://github.com/peonPing/peon-pet. Sadly tightly coupled to Claude Code.

## Disclaimer

All existing images were AI-generated. I take no credit for them. The orc sprite set comes from the OG peon pet.

The 2b sprite map was edited and assembled by me using images from Gemini
and [LibreSprite](https://libresprite.github.io/#!/). You can find the original sprite sheets in the assets folder.