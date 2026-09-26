import pytest

from hermetiks.core.ducking import ATTACK, HOLD, RELEASE, DuckRamp, ease


def run(ramp, seconds, want, dt=1 / 60):
    out = []
    for _ in range(int(seconds / dt)):
        out.append(ramp.step(dt, want))
    return out


def test_ease_is_smooth_and_bounded():
    assert ease(0) == 0 and ease(1) == 1 and ease(0.5) == 0.5
    assert all(ease(i / 100) <= ease((i + 1) / 100) for i in range(100))


def test_fade_down_is_fast_but_gradual():
    ramp = DuckRamp()
    values = run(ramp, ATTACK * 1.2, want=True)
    assert values[-1] == 1.0
    assert 0 < values[0] < 0.2  # not an instant cut
    assert all(b >= a for a, b in zip(values, values[1:]))
    assert ATTACK * 60 - 2 <= values.index(1.0) <= ATTACK * 60 + 2  # reaches the level in about ATTACK seconds


def test_fade_up_waits_for_hold_then_takes_release_time():
    ramp = DuckRamp()
    run(ramp, 0.5, want=True)
    held = run(ramp, HOLD * 0.9, want=False)
    assert held[-1] == 1.0  # still ducked during the hold (quick consecutive clips don't pump the music)
    back = run(ramp, HOLD + RELEASE + 0.1, want=False)
    assert back[-1] == 0.0
    assert all(b <= a for a, b in zip(back, back[1:]))


def test_a_new_clip_during_release_ducks_again_from_where_it_is():
    ramp = DuckRamp()
    run(ramp, 0.5, want=True)
    run(ramp, HOLD + RELEASE / 2, want=False)
    mid = ramp.p
    assert 0 < mid < 1
    assert ramp.step(1 / 60, True) > mid


@pytest.mark.parametrize("level,p,expected", [(0.3, 0, 1.0), (0.3, 1, 0.3), (0.0, 1, 0.0), (1.0, 1, 1.0)])
def test_volume_factor(level, p, expected):
    ramp = DuckRamp()
    ramp.p = p
    assert ramp.factor(level) == pytest.approx(expected)


def test_factor_never_leaves_range():
    ramp = DuckRamp()
    for i in range(101):
        ramp.p = i / 100
        assert 0.25 <= ramp.factor(0.25) <= 1.0


@pytest.mark.parametrize("typed,expected", [
    ("/spotify.exe/", ["spotify"]), ("Spotify.exe", ["spotify"]), ("spotify", ["spotify"]),
    (r"C:\Users\me\AppData\Spotify.exe", ["spotify"]), ('"spotify.exe"', ["spotify"]),
    ("spotify.exe, chrome.exe; vlc", ["spotify", "chrome", "vlc"]), ("  ,, / ", []), ("", []),
])
def test_app_names_are_read_tolerantly(typed, expected):
    from hermetiks.core.ducking import normalize_apps
    assert normalize_apps(typed) == expected


def test_matching_by_process_name():
    from hermetiks.core.ducking import app_matches
    assert app_matches("Spotify.exe", ["spotify"]) and app_matches("spotify.exe", ["spotify"])
    assert app_matches("chrome.exe", ["chrome"]) and not app_matches("chrome.exe", ["spotify"])
    assert app_matches("SpotifyHelper.exe", ["spotify"])       # substring for real names
    assert not app_matches("obs64.exe", ["ob"])                # very short tokens must match exactly
