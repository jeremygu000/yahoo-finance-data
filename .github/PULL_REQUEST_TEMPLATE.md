## Summary

Provide a clear and concise summary of your changes. Link any related issues using `Closes #123` or `Fixes #456`.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## Changes Made

Describe the changes you made in detail.

## Testing

Describe the tests you ran to verify the changes. Include the commands used:

```bash
uv run pytest -v
```

## Checklist

- [ ] My code follows the code style of this project (`black`, `mypy --strict`)
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Frontend changes (if any) pass `pnpm lint` and `pnpm build`

## Additional Notes

Add any other information that reviewers should know here.
