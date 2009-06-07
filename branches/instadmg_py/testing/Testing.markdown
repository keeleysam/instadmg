InstaDMG Testing Suite
========

Document the testing suite.

Each testing unit should be an archive file (dmg, flat package, or a folder), a configuration file, and a post-flight test.

Configuration files are not yet supported (or really defined yet).

The post-flight test should test whether the image has the proper items in it, but for the moment this is not yet implimented.

Test A
--------

A flat package inside a dmg with a folder (TestA) that gets put in /Applications with a single file in it (PackageInstall1). Additionally a post-flight script should create two files in the same folder (PostFlight1 and PostFlight2). All items should be root:wheel permissions.

Test B
--------

A flat package inside a folder that installs a folder (TestB) in /Applications.