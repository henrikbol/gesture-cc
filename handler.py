from __future__ import annotations

import math
import time
from typing import Final

import cv2
import mediapipe as mp
import numpy as np
from numpy.typing import NDArray
import rtmidi

# ---------------- MIDI SETUP ---------------- #

MIDI_PORT_NAME_SUBSTRING: Final[str] = "IAC"  # part of your IAC port name
MIDI_CHANNEL: Final[int] = 0                  # 0 = MIDI channel 1

# Assign CC numbers for each line
CC_LEFT_HAND: Final[int] = 20         # left thumb-index distance
CC_RIGHT_HAND: Final[int] = 21        # right thumb-index distance
CC_THUMB_TO_THUMB: Final[int] = 22    # left thumb - right thumb
CC_INDEX_TO_INDEX: Final[int] = 23    # left index - right index

# rough distance range in pixels (tweak for your framing)
MIN_DIST_PX: Final[int] = 20
MAX_DIST_PX: Final[int] = 400


def find_midi_port(port_name_substring: str = MIDI_PORT_NAME_SUBSTRING) -> rtmidi.MidiOut:
    """Find and open a MIDI output port matching the substring, or create a virtual port."""
    midi_out = rtmidi.MidiOut()
    ports: list[str] = midi_out.get_ports()
    print("Available MIDI ports:", ports)
    for i, name in enumerate(ports):
        if port_name_substring in name:
            midi_out.open_port(i)
            print(f"Opened MIDI port: {name}")
            return midi_out

    # fallback: virtual port
    midi_out.open_virtual_port("PoseHandControl")
    print("Opened virtual MIDI port: PoseHandControl (no IAC found)")
    return midi_out

def normalize_to_cc(
    dist_px: float,
    min_d: float = MIN_DIST_PX,
    max_d: float = MAX_DIST_PX,
) -> int:
    """Normalize a pixel distance to a MIDI CC value (0-127)."""
    d = max(min_d, min(max_d, dist_px))  # clamp
    norm = (d - min_d) / (max_d - min_d)
    return int(norm * 127)


def send_cc(
    midi_out: rtmidi.MidiOut,
    cc_number: int,
    value: int,
    channel: int = MIDI_CHANNEL,
) -> None:
    """Send a MIDI Control Change message."""
    status = 0xB0 | (channel & 0x0F)
    value = max(0, min(127, int(value)))
    msg = [status, cc_number & 0x7F, value]
    midi_out.send_message(msg)


def draw_line_info(
    frame: NDArray[np.uint8],
    p1: tuple[int, int] | None,
    p2: tuple[int, int] | None,
    label_text: str,
    color: tuple[int, int, int],
    midi_out: rtmidi.MidiOut | None = None,
    cc_number: int | None = None,
) -> tuple[float, float] | None:
    """Draw a line between two points with distance/angle info and optionally send MIDI CC.

    Args:
        frame: The OpenCV image frame to draw on.
        p1: First point (x, y) or None.
        p2: Second point (x, y) or None.
        label_text: Label to display near the line.
        color: BGR color tuple for the line.
        midi_out: Optional MIDI output port.
        cc_number: Optional CC number to send.

    Returns:
        Tuple of (distance, angle) if both points exist, None otherwise.
    """
    if p1 is None or p2 is None:
        return None

    x1, y1 = p1
    x2, y2 = p2

    # distance in pixels
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    # angle in degrees (atan2 handles full circle)
    angle = math.degrees(math.atan2((y2 - y1), (x2 - x1)))

    # draw the line
    cv2.line(frame, (x1, y1), (x2, y2), color, 2)

    # text near midpoint
    mid_x = int((x1 + x2) / 2)
    mid_y = int((y1 + y2) / 2) - 10
    text = f"{label_text} d={normalize_to_cc(dist):.1f}px a={angle:.1f}°"
    cv2.putText(
        frame,
        text,
        (mid_x, mid_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )

    # optional MIDI
    if cc_number is not None and midi_out is not None:
        cc_val = normalize_to_cc(dist)
        send_cc(midi_out, cc_number, cc_val)

    return dist, angle

# Type alias for fingertip coordinates
CoordsDict = dict[str, dict[str, tuple[int, int] | None]]


def run() -> None:
    """Main entry point: run the hand gesture MIDI controller."""
    # -------------- MIDI SETUP -------------- #
    midi_out = find_midi_port()

    # -------------- MEDIAPIPE SETUP -------------- #
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)

    hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    print("Press 'q' to quit.")

    last_send: float = 0.0
    send_interval: float = 1 / 30.0  # send MIDI ~30 times per second

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Mirror frame
            frame = cv2.flip(frame, 1)

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(image_rgb)

            h, w, _ = frame.shape

            # Store fingertip coordinates
            coords: CoordsDict = {
                "Left": {"thumb": None, "index": None},
                "Right": {"thumb": None, "index": None},
            }

            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness in zip(
                    results.multi_hand_landmarks, results.multi_handedness
                ):
                    label: str = handedness.classification[0].label  # "Left" or "Right"

                    thumb_tip = hand_landmarks.landmark[4]
                    index_tip = hand_landmarks.landmark[8]

                    t_x, t_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                    i_x, i_y = int(index_tip.x * w), int(index_tip.y * h)

                    coords[label]["thumb"] = (t_x, t_y)
                    coords[label]["index"] = (i_x, i_y)

                    # draw fingertip markers
                    cv2.circle(frame, (t_x, t_y), 8, (0, 255, 0), -1)  # thumb: green
                    cv2.circle(frame, (i_x, i_y), 8, (0, 0, 255), -1)  # index: red

                    # thumb ↔ index line on this hand
                    cv2.line(frame, (t_x, t_y), (i_x, i_y), (255, 0, 0), 2)

                    # Optional: skeleton
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS
                    )

            now = time.time()
            send_midi_now = (now - last_send) > send_interval

            # Left and right fingertips
            left_thumb = coords["Left"]["thumb"]
            left_index = coords["Left"]["index"]
            right_thumb = coords["Right"]["thumb"]
            right_index = coords["Right"]["index"]

            # Same-hand lines (left, right)
            if send_midi_now:
                draw_line_info(
                    frame, left_thumb, left_index, "L T-I", (255, 0, 0), midi_out, CC_LEFT_HAND
                )
                draw_line_info(
                    frame, right_thumb, right_index, "R T-I", (255, 0, 0), midi_out, CC_RIGHT_HAND
                )
                # Cross-hand: thumb–thumb
                draw_line_info(
                    frame, left_thumb, right_thumb, "T-T", (0, 255, 255), midi_out, CC_THUMB_TO_THUMB
                )
                # Cross-hand: index–index
                draw_line_info(
                    frame, left_index, right_index, "I-I", (255, 255, 0), midi_out, CC_INDEX_TO_INDEX
                )
                last_send = now
            else:
                # draw without sending MIDI (angle/dist still useful visually)
                draw_line_info(frame, left_thumb, left_index, "L T-I", (255, 0, 0))
                draw_line_info(frame, right_thumb, right_index, "R T-I", (255, 0, 0))
                draw_line_info(frame, left_thumb, right_thumb, "T-T", (0, 255, 255))
                draw_line_info(frame, left_index, right_index, "I-I", (255, 255, 0))

            cv2.imshow("Hand demo – distances, angles, MIDI", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()


if __name__ == "__main__":
    run()