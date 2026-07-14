# SRPsummer2026
Sustainable Research Pathways 2026 summer project

## Instructions for cloning

First, create a fork of this repository and clone your fork:

```
git clone git@github.com:<username>/SRPsummer2026.git
```

Add a remote `upstream` to point to the upstream repository:

```
git remote add upstream git@github.com:phi-l-l-ip-thomas/SRPsummer2026.git
```

You should see two remote endpoints, `origin` points to your fork and `upstream` points to the main repository:

```
$ git remote -v
origin	git@github.com:<username>/SRPsummer2026.git (fetch)
origin	git@github.com:<username>/SRPsummer2026.git (push)
upstream	git@github.com:phi-l-l-ip-thomas/SRPsummer2026.git (fetch)
upstream	git@github.com:phi-l-l-ip-thomas/SRPsummer2026.git (push)
```

Checkout the `main` branch of your local repository and and sync with the `upstream` endpoint:

```
git checkout main
git pull upstream main
```

To push the sync'd changes to your fork:

```
git push origin main
```

Do not use your main branch to make any changes; this branch is used
to sync changes from `upstream` because all pull requests get pushed to the `main`
branch in the `upstream` repository. 
Instead, create a feature branch from main as follows:

# When contributing via your fork

First, sync your `main` branch, as shown above. Then create your feature branch from `main`:

```
git checkout main
git checkout -b <FEATURE BRANCH>
git add <file1> <file2>
git commit -m <COMMIT MESSAGE>
git push origin <FEATURE BRANCH>
```

Once finished making changes, create a pull request to merge the changes from the feature branch in your `origin` repository to the main branch in the `upstream` repository.

