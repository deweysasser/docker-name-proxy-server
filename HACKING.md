# How to contribute to this project

## LICENSE

Per the Apache License, v2.0, any contributions either directly pushed
to this project or submitted via Pull Request, the submitter agrees
and warrants that they have full rights to submit their contributions
and that they will be licensed under the package license.

## Branches and Docker Repositories

The main repositor of this project had 3 branchs

  * experimental -- Anything goes.  This branch may be reverted,
    reset, force pushed, whatever.  Expect rebases and commit
    consolidation.  This branch exists to feed a public build
    of exploratory solutions.

  * master -- integration branch used to received pull requests and
    otherwise test the package before including it in a release.

  * release -- considered the 'stable' branch, each point on this
    branch should be a working, complete package.

These branches are all automatically built and made available on
https://hub.docker.com/r/deweysasser/name-proxy-server/, as follows:

  * experimental -> 'experimental' tag
  * master -> 'unstable' tag
  * release -> 'latest' tag

If you want the latest, working code, just pull the default tag.  

If you want the latest features that haven't yet been adequately
proven in the real world but are unlikely to revert or change in
interface (because, for example, you'd like to prove them), pull
'unstable'.  Consider this alpha to beta quality code.

If you want to try the absolute bleeding edge and don't mind the risk
of a little bleeding of your own, pull 'experimental'.


## Maintainer

This project is maintained by Dewey Sasser <dewey@sasser.com>.  Please
submit all PRs through Github.

Occationally, Dewey will grant a contributor direct push access to a
repository.  If you are one of those contributor, you may coordinate
pushes to experimental or master with Dewey.  Dewey should be the only
one pushing to release.  There is nothing enforcing this -- if you've
been granted direct push access, you're trusted enough to follow this
process.

