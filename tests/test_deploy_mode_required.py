"""`--mode` must be an explicit choice, never a silent default (B-028 Task 1).

Article two was deployed with `deploy_to_blog --mode post` — a PR straight into
`_posts/` — skipping the B-013 live review stage entirely. The RCA's root cause
was not the operator: `_parse_args` set ``default="post"``, so running the
command exactly as five docs described it produced an **unreviewed publish with
no error and no warning**.

Neither value is a safe default. `post` skips review; `review` would write to the
blog's live branch on a bare invocation, which is worse. Forcing an explicit
choice removes the accident without picking a wrong default.

These tests exist so a future tidy-up cannot quietly restore the default.
"""

from __future__ import annotations

import pytest

import scripts.deploy_to_blog as dtb


class TestModeIsRequired:
    """A bare invocation must fail loudly rather than publish."""

    def test_missing_mode_exits_non_zero(self) -> None:
        with pytest.raises(SystemExit) as exc:
            dtb._parse_args(["--article", "output/posts/x.md"])

        assert exc.value.code != 0

    def test_missing_mode_names_both_choices(self, capsys) -> None:
        """The error has to tell the operator what to type instead."""
        with pytest.raises(SystemExit):
            dtb._parse_args(["--article", "output/posts/x.md"])

        message = capsys.readouterr().err
        assert "--mode" in message
        assert "post" in message
        assert "review" in message

    def test_no_default_is_configured(self) -> None:
        """Guards the actual regression: a default reintroduced later.

        Asserting on parser configuration rather than only on behaviour means
        this fails even if someone adds a default *and* a required flag, which
        argparse would otherwise let pass silently.
        """
        parser = dtb._build_parser()
        action = next(a for a in parser._actions if a.dest == "mode")

        assert action.required is True
        assert action.default is None


class TestExplicitModeStillWorks:
    """The fix must not break either sanctioned invocation."""

    @pytest.mark.parametrize("mode", ["post", "review"])
    def test_explicit_mode_parses(self, mode: str) -> None:
        args = dtb._parse_args(["--article", "output/posts/x.md", "--mode", mode])

        assert args.mode == mode

    def test_other_defaults_are_untouched(self) -> None:
        """Scope check: only `--mode` loses its default."""
        args = dtb._parse_args(
            ["--article", "output/posts/x.md", "--mode", "review"],
        )

        assert args.dry_run is False
        assert args.live_branch
