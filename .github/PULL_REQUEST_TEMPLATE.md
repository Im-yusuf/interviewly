**What this changes and why**

- [ ] `python3 -m unittest discover tests` passes
- [ ] `python3 scripts/build_antigravity.py` re-run if skills, agents, references or scripts changed
- [ ] `claude plugin validate .` passes
- [ ] The evals for the skills this touches were run (`claude plugin eval . --case <name> --scaffold --allow-tools Bash Write Edit WebFetch --runs 1`), or this changes no skill behaviour
- [ ] `CHANGELOG.md` has an entry, and both manifests have the new version, if this ships
- [ ] Examples, tests and evals use the fictional sample data, never a real CV, project or contact detail
