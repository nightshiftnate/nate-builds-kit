# 7 rules that make Claude check its renders

The seven rules from the "7 rules for checking renders" carousel. They are lines from the CLAUDE.md I keep next to my edits, quoted as written. The full file and the checker script are in [edit-check/](../edit-check/): the rules live in [edit-check/CLAUDE.md](../edit-check/CLAUDE.md) and they point at `edit_check.py`.

To use them, copy the file into your edit folder:

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
cp edit-check/CLAUDE.md edit-check/edit_check.py ~/my-edit-folder/
```

## The rules

1. After every render, check the file before showing me a cut. Run `python3 edit_check.py <render>.mp4`.
2. If any line says FAIL, fix the cause in the edit, re-render, and run the check again. Repeat until every check passes, up to three tries.
3. If it still fails after three, stop and show me the FAIL lines and what you tried. Don't show me a cut that has a FAIL.
4. Don't change the thresholds at the top of `edit_check.py`, and don't pass `--max-duration`, to make a check pass.
5. If the check can't run at all (it exits with an error instead of PASS/FAIL lines), stop and tell me; that is not a pass.
6. When you show me the cut, include the final `N/M PASS` line.
7. For each note: make only that change, re-render, run the check, then show me the cut. Don't bundle in other fixes.

The checks measure the file. They can't tell you whether the cut looks good. That part is still your call.
