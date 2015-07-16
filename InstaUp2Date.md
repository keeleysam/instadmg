InstaUp2Date is a helper application for InstaDMG and is included in the download/svn checkout.

# Introduction #

The latest version of this document can always be found at: http://code.google.com/p/instadmg/wiki/InstaUp2Date

!InstaDMG is focused on producing a 'clean,' un-booted image with the same result every time it runs. There are certain optimizations for speed and to reduce the human time investment in using it repeatedly. However, many people need to produce several different images with specific load-sets on them, maintain their environments by creating updated images regularly, and manage the included packages from a centralized repository. For those purposes, manual interaction with !InstaDMG becomes a little unwieldy.

To alleviate this workflow issue, included with !InstaDMG is an add-on program, InstaUp2Date.  It uses catalog files to manage the moving parts that !InstaDMG interacts with, listing the software and settings that should go into a particular image. These catalogs can also reference other files that therefore act as generic 'pools' of software and settings, allowing you to make adjustments in only the applicable file when something changes.

At this point almost everything is command-line only, but InstaUp2Date is written in Python (utilizing Python's access to native Objective-C objects via Bridge Support) with the possibility of sliding a Cocoa GUI on in mind.

# Installation #

InstaUp2Date is included with InstaDMG, so no installation is necessary. It is in the InstaDMG/AddOns/InstaUp2Date directory, and should be left there.

# Using InstaUp2Date #

To use InstaUp2Date you need to have a few things setup already:
  1. A Base OS image should already be in InstaDMG/InstallerFiles/!BaseOS OR InstaDMG/InstallerFiles/InstallerDiscs (preferred)
  1. The catalog file(s) you'd like to utilize should be in InstaDMG/AddOns/InstaUp2Date/CatalogFiles
  1. Any mpkgs, pkgs, or .apps(or dmgs with those contained therein) referenced in the catalog files that aren't referenced by url should already be placed in InstaDMG/InstallerFiles/InstaUp2DatePackages (designated for custom items you create yourself, e.g. createUser)

With those items in place, you call InstaUp2Date like this:

`/path/to/instaUp2Date.py <<catalog file name, without the .catalog extension>>`

As is possible when arranged locally with !InstaDMG, pkgs (flat or older-style bundles), mpkgs, plain 'drag-and-drop-to-install' applications, and dmgs containing any of the above (heretofore referred to as 'installable items') can all be queued up in a catalog file.
The way they are referenced in a catalog file is in one of three ways:
  1. The full path to the installable items (should be on the local file system, most reliably on the same volume as !InstaDMG)
  1. The filename to search for the installable items by, either within the InstaDMG/InstallerFiles/InstaUp2DatePackages, InstaDMG/!Caches/InstaUp2DateCache, or another directory specified with the optional --add-source-folder flag
  1. An http(s) reference to installable items(flat pkgs and dmgs are recommended, for more reliable transfer)
Example:
> Firefox 3.6.12	http://download.mozilla.org/?product=firefox-3.6.12&os=osx&lang=en-US	sha1:add2c49a346042187eccb576b65af692fbac9661
Any packages that are referenced with http urls are downloaded by InstaUp2Date when evaluated and placed in the InstaDMG/!Caches/InstaUp2DateCache folder.

The most common usage of InstaUp2Date is when you would like to run !InstaDMG immediately after preparing the folders for it, which is accomplished by adding either the `-p` or `--process` to the invocation. When called like this, InstaUp2Date will add appropriate command-line switches for !InstaDMG to use, and needs to be done as root like so:

`sudo /path/to/instaUp2Date.py --process <<catalog file>>`

# Command Line Options #

There are several other command line options that InstaUp2Date will accept:

`-h` or `--help`		Print the usage information and exit.

`-v` or `--version`		Print version information and quit.

`-p` or `--process`		As described above, runs InstaDMG after successfully setting things up, along with any of the following options

`-a FILE_PATH` or `--add-catalog=FILE_PATH` Add the items in this catalog file to all catalog files processed. Can be called multiple times

`--instadmg-scratch-folder=FOLDER_PATH` 		Tell InstaDMG to use FOLDER\_PATH as the scratch folder

`--instadmg-output-folder=FOLDER_PATH` 			Tell InstaDMG to place the output image in FOLDER\_PATH

`--add-catalog-folder=FILE_PATH` 				Set the folders searched for catalog files

`--set-cache-folder=FILE_PATH` 					Set the folder used to store downloaded files

`--add-source-folder=FILE_PATH` 				Set the folders searched for items to install

`--restore-onto-volume=VOLUME` 					After creating the image, restore onto volume.
> WARNING: this will destroy all data on the volume

When running InstaUp2Date, you can tell it to use multiple 'master' catalogs so you can create a series of images at a time. This is most useful if you are using the `--process` flag, as at the start of each run the setup from the previous run is wiped out. However it is helpful to add new catalog files one at a time to verify that, for example, the syntax is valid, or that you have download access to all of the relevant http(s) referenced flat pkgs or dmgs.

# Creating Catalog Files #

Specifics for how to create catalog files are located in the sample.catalog file in InstaDMG/AddOns/InstaUp2Date/CatalogFiles

The Base OS image build numbers are explicitly checked to verify that a retail install disc is used, to ensure compatibility with the widest range of hardware possible. To use an 'installer choices' file, which customizes .mpkg installs, you need to reference it with its checksum in a Setting line at the beginning of the relevant catalog file.  De-coupling the 'generic' installable items for an organization from the vanilla updates and items that are department-specific is how you can logically divide the catalog files to create dependencies.  Using 'include-file' Setting lines in your catalog file is how you would setup these links between catalogs.

## Creating Checksums ##

Since all of the installable item lines in a catalog file also require checksums, there is an included tool to help you produce them via the openssl binary. The tool is conveniently called "checksum.py" and is located in the same folder as the !instaup2date.py script. To use it just call it like this:

`/path/to/checksum.py <<path/to.DMG_or_PKG>>`

The path you use can either be the POSIX "/tmp/thisfile.dmg" format, or the http(s) url (`http://somewhere.com/myGreatPkg.dmg`. The latter form is probably the more useful for packages that you don't create yourself, as InstaUp2Date will cache them and then you don't have to move them with you if you use your catalog file on a new computer.  When creating the checksum, checksum.py will download the item (so that it can be worked on locally), but it will be purged from your system on reboot.

# Workflow Example #

Say we're creating images for an organization that has Office 2008 on all computers, one department that needs iPhoto, and another that has brand new hardware.  It is recommended that you would create the following:
  1. one base catalog file with the OS and its vanilla updates to include the majority of the organization's hardware (machines older than the release of the most recent OS point update, with rare caveats)
  1. one general, cross-organization catalog to include Office and other 'shared' apps or settings
  1. one general iPhoto (and its updates)-specific catalog file, which references the installer choices xml you'd create to limit iLife to that one application

And to those building blocks, you would add:
  1. A temporary base catalog file with the new hardware's specific 'grey disc' build number and updates,
  1. And specific 'master' catalog files for the organization's generic build and the iPhoto build, with 'include-file' lines for each applicable base and general combination

# Notes #

  * InstaUpToDate has the same resources that !InstaDMG is slowly being re-engineered to utilize. That being said, at present it only allows the automation of setup before you run InstaDMG, so there is very little you can do using InstaUp2Date that was not already possible with !InstaDMG.  Should you find an incompatibility, please revert to manually arranging folders with the traditional InstaDMG-only workflow before filing bug reports to verify your installable items are not the issue.

  * The parts are still in a somewhat rough form. It is used by many groups with different workflows, and is working for them, but testing is not 100% complete at this point.  No warrantee is granted or implied regarding compatibility or functionality.

  * Additions and bug-fixes are always welcome

  * At the moment error reporting is very rough. Often, reviewing the code is required to figure out what went wrong.

  * InstaUp2Date is under the same license as !InstaDMG.

# Room for Improvement #

These are ideas that InstaUp2Date might be able to utilize:

  * There are a bunch of problems that combining !InstaDMG and InstaUp2Date together into one program would solve. This includes: having pre/postflight scripts, adding items without pkgs, and improving the logging/feedback/exception handling.

  * Add a Cocoa GUI.

  * Do more pre-flighting of the items to make sure that they include pkgs.

  * Allow for some introspection into pkgs... possibly even use a union mount to allow pre and postflight scripts to be edited without changing anything. This would require the first item.