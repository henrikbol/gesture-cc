"""Entry point for the midi-gestures hand tracking MIDI controller."""

from .handler import run

def main() -> None:
    """Run the hand gesture MIDI controller."""
    run()


if __name__ == "__main__":
    main()
