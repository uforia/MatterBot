Contributing is simple! Everything is welcome, whether it's a new feature, improvement, style comment, etc.

Just do one or more of the following:

- Request the feature directly
- Open an issue
- Send a pull request

If you send a pull request, please run the test suite first. It is stdlib-only (no
third-party dependencies needed) and also runs in CI on every PR:

```
python3 -m unittest discover -s tests -v
python3 feed_audit.py --check   # static load-contract check for feed modules
```

TIA! -- A. Eijkhoudt
