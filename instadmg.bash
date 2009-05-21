#!/bin/bash

#
# instadmg - script to automate creating ASR disk images
#

#
# Maintained by the InstaDMG dev team @ http://code.google.com/p/instadmg/
# Latest news, releases, and user forums @ http://www.afp548.com
#

SVN_REVISION=`/bin/echo '$Revision$' | /usr/bin/awk '{ print $2 }'`
VERSION="1.5pre (svn revision: $SVN_REVISION)"
PROGRAM=$( (basename $0) )


#<!------------------- Setup Environment ------------------->

IFS=$'\n'

unset -f unalias
unalias -a
unset -f command

# set path to a known path
PATH="/usr/bin:/bin:/usr/sbin:/sbin"
export PATH

# Change the working directory to the one containing the instadmg.bash script
cd "`/usr/bin/dirname "$0"`"

# Environment variables used by the installer command
export COMMAND_LINE_INSTALL=1
export CM_BUILD=CM_BUILD


#<!------------------- Variable Defaults ------------------->

# Set the creation date in a variable so it's consistant during execution.
CREATE_DATE=`/bin/date +%y-%m-%d`

# Default values
DMG_SIZE=300g									# Size of the sparce image, this shoud be large enough
ISO_CODE="en"									# ISO code that installer will use for the install language
DISABLE_CHROOT=false							# Use a chroot jail while installing updates
DISABLE_BASE_IMAGE_CACHING=false				# setting this to true turns off caching

# Default folders
INSTALLER_FOLDER="./InstallerFiles/BaseOS"		# Images of install DVDs
UPDATE_FOLDER="./InstallerFiles/BaseUpdates"	# System update pkg's, numbered folders provide the ordering
CUSTOM_FOLDER="./InstallerFiles/CustomPKG"		# All other update pkg's
ASR_FOLDER="./OutputFiles"						# Destination of the ASR images
BASE_IMAGE_CACHE="./Caches/BaseImageCache"		# Cached images named by checksums
LOG_FOLDER="./Logs"
DMG_MOUNT_LOCATION="/private/tmp"				# DMGs will be mounted at a location inside of this folder

# TODO: make sure that the cached images are not indexed

# Default Names
DMG_BASE_NAME=`/usr/bin/uuidgen`				# Name of the intermediary image
MOUNT_FOLDER_TEMPLATE="${PROGRAM}_mount_folder.XXXXXX"
MOUNT_POINT_TEMPLATE="${PROGRAM}_mount_point.XXXXXX"
SOURCE_FOLDER_TEMPLATE="${PROGRAM}_package.XXXXXX"
ASR_OUPUT_FILE_NAME="${CREATE_DATE}.dmg"		# Name of the final image file
ASR_FILESYSTEM_NAME="InstaDMG"					# Name of the filesystem in the final image

# Names allowed for the primary installer disk
ALLOWED_INSTALLER_DISK_NAMES=("Mac OS X Install Disc 1.dmg" "Mac OS X Install DVD.dmg")


# Default log names. The PKG log is a more consise history of what was installed.
DATE_STRING=`/bin/date +%y.%m.%d-%H.%M`
LOG_FILE="${LOG_FOLDER}/${DATE_STRING}.debug.log"		# The debug log
PKG_LOG="${LOG_FOLDER}/${DATE_STRING}.package.log"		# List of packages installed


#<!-------------------- Working Variable ------------------->
HOST_MOUNT_FOLDER=''					# Enclosing folder for the base image mount point, and othes if not using chroot
TARGET_TEMP_FOLDER=''					# If using chroot packages will be copied into temp folders in here before install

BASE_IMAGE_FILE=''						# Location of the installer dmg
BASE_IMAGE_CHECKSUM=''					# Checksum reported by diskutil for the OS Instal disk image
BASE_IMAGE_CACHE_FOUND=false

CURRENT_IMAGE_MOUNT=''					# Where the (read-only) target is mounted
SCRATCH_FILE_LOCATION=''				# Location of the scratch file that is grafted onto the CURRENT_IMAGE_MOUNT

CURRENT_OS_INSTALL_FILE=''				# Location of the primary installer disk
CURRENT_OS_INSTALL_MOUNT=''				# Mounted location of the primary installer disk
CURRENT_OS_INSTALL_AUTOMOUNTED=false	# 

OS_REV_MAJOR=''
OS_REV_MINOR=''
CPU_TYPE=''

# ASR target volume. Make sure you set it to the correct thing! In a future release this, and most variables, will be a getopts parameter.
ASR_TARGET_VOLUME="/Volumes/foo"


#<!----------------------- Logging ------------------------->

# Logging levels
# Error:		always logged to everything
# Section:		CONSOLE level 1 and higher, PACKAGE level 1 and higher
# Warning:		CONSOLE level 2 and higher, PACKAGE level 1 and higher
# Information:	CONSOLE level 2 and higher, PACKAGE level 2 and higher
# Detail:		CONSOLE level 3 and higher, PACKAGE level 3 and higher
# Detail 2:		CONSOLE level 4 and higher, PACKAGE leval 4 and higher
CONSOLE_LOG_LEVEL=3
PACKAGE_LOG_LEVEL=2

# Log a message - takes up to two arguments
#	The first argument is the message to send. If blank log prints the date to the standard places for the selcted log level
#	The second argument tells the type of message. The default is information. The options are:
#		section		- header announcing that a new section is being started
#		warning		- non-fatal warning
#		error		- non-recoverable error
#		information	- general information
#		detail		- verbose detail

# everything will always be logged to the full log
# depending on the second argument and the loggin levels for CONSOLE_LOG_LEVEL and PACKAGE_LOG_LEVEL the following will be logged

# Detail 2 is lines that begin with "installer:" that don't match a couple of other criteria

# commands should all have the following appended to them:
#	| (while read INPUT; do log "$INPUT " information; done)

ERROR_LOG_FORMAT="ERROR: %s\n"
SECTION_LOG_FORMAT="###### %s ######\n"
WARNING_LOG_FORMAT="WARNING: %s\n"
SUBPACKAGE_LOG_FORMAT="		%s\n"
INFORMATION_LOG_FORMAT="	%s\n"
DETAIL_LOG_FORMAT="		%s\n"

log() {
	if [ -z "$1" ] || [ "$1" == "" ] || [ "$1" == "#" ]; then
		# there is nothing to log
		return
	else
		MESSAGE="$1"
	fi
	
	if [ -z "$2" ]; then
		LEVEL="information"
	else
		LEVEL="$2"
	fi	
	
	if [ "$LEVEL" == "error-nolog" ]; then
		/usr/bin/printf "$SECTION_LOG_FORMAT" "$MESSAGE" 1>&2
	fi
	
	if [ "$LEVEL" == "error" ]; then
		/usr/bin/printf "$SECTION_LOG_FORMAT" "$MESSAGE" | /usr/bin/tee "$LOG_FILE" "$PKG_LOG" 1>&2
	fi

	if [ "$LEVEL" == "section" ]; then
		TIMESTAMP=`date "+%H:%M:%S"`
		/usr/bin/printf "$TIMESTAMP $SECTION_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
	
		if [ $CONSOLE_LOG_LEVEL -ge 1 ]; then 
			/usr/bin/printf "$TIMESTAMP $SECTION_LOG_FORMAT" "$MESSAGE"
		fi
		if [ $PACKAGE_LOG_LEVEL -ge 1 ]; then
			/usr/bin/printf "$TIMESTAMP $SECTION_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
		fi
	fi
	
	if [ "$LEVEL" == "warning" ]; then
		/usr/bin/printf "$WARNING_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
	
		if [ $CONSOLE_LOG_LEVEL -ge 2 ]; then 
			/usr/bin/printf "$WARNING_LOG_FORMAT" "$MESSAGE"
		fi
		if [ $PACKAGE_LOG_LEVEL -ge 1 ]; then
			/usr/bin/printf "$WARNING_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
		fi
	fi
	
	if [ "$LEVEL" == "information" ]; then
		/usr/bin/printf "$INFORMATION_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
	
		if [ $CONSOLE_LOG_LEVEL -ge 2 ]; then 
			/usr/bin/printf "$INFORMATION_LOG_FORMAT" "$MESSAGE"
		fi
		if [ $PACKAGE_LOG_LEVEL -ge 2 ]; then
			/usr/bin/printf "$INFORMATION_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
		fi
	fi
	
	if [ "$LEVEL" == "detail" ]; then
		/usr/bin/printf "$DETAIL_LOG_FORMAT" "$MESSAGE" >> "$LOG_FILE"
		
		# here we are going to split the "detail" and "detail 2" groups
		# the different packages will also cause "informational" messages
		
		if [[ $MESSAGE == *installer:\ Installing* ]]; then
			FILTERED_MESSAGE=`/bin/echo "$MESSAGE" | /usr/bin/awk 'sub("installer: ", "")'`
		
			if [[ $MESSAGE == *base\ path* ]]; then
				if [ $CONSOLE_LOG_LEVEL -ge 3 ]; then 
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE"
				fi
				if [ $PACKAGE_LOG_LEVEL -ge 3 ]; then
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE" >> "$PKG_LOG"
				fi
			else
				if [ $CONSOLE_LOG_LEVEL -ge 2 ]; then 
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE"
				fi
				if [ $PACKAGE_LOG_LEVEL -ge 2 ]; then
					/usr/bin/printf "$SUBPACKAGE_LOG_FORMAT" "$FILTERED_MESSAGE" >> "$PKG_LOG"
				fi
			fi
		elif [[ $MESSAGE == installer:* ]]; then
		
			FILTERED_MESSAGE=`/bin/echo "$MESSAGE" | /usr/bin/awk 'sub("installer: ", "")'`
			
			if [ $CONSOLE_LOG_LEVEL -ge 4 ]; then 
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$FILTERED_MESSAGE"
			fi
			if [ $PACKAGE_LOG_LEVEL -ge 4 ]; then
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$FILTERED_MESSAGE" >> "$PKG_LOG"
			fi
		else
			if [ $CONSOLE_LOG_LEVEL -ge 3 ]; then 
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$MESSAGE"
			fi
			if [ $PACKAGE_LOG_LEVEL -ge 3 ]; then
				/usr/bin/printf "$DETAIL_LOG_FORMAT" "$MESSAGE" >> "$PKG_LOG"
			fi
		fi
	fi
}

#<!----------------------- Functions ----------------------->

bail() {	
	#If we get here theres a problem, print the usage message and then exit with a non-zero status
	usage $1
}

version() {
	# Show the version number
	/bin/echo "$PROGRAM version $VERSION"
	exit 0
}

usage() {
	# Usage format
cat <<EOF
Usage:	$PROGRAM [options]

Note:	This program must be run as root (sudo is acceptable)

Options:
	-b <folder path>	Look for the base image in this folder ($INSTALLER_FOLDER)
	-c <folder path>	Look for custom pkgs in this folder ($CUSTOM_FOLDER)
	-h			Print the useage information (this) and exit
	-i <iso code>		Use <iso code> for the installer language ($ISO_CODE)
	-l <folder path>	Set the folder to use as the log folder ($LOG_FOLDER)
	-m <name>		The file name to use for the ouput file. '.dmg' will be appended as needed. ($ASR_OUPUT_FILE_NAME)
	-n <name>		The volume name to use for the output file. ($ASR_FILESYSTEM_NAME)
	-o <folder path>	Set the folder to use as the output folder ($ASR_FOLDER)
	-q			Quiet: print only errors to the console
	-r			Disable using chroot for package installs ($DISABLE_CHROOT)
	-t <folder path>	Create a scratch space in this folder ($DMG_MOUNT_LOCATION)
	-u <folder path>	Use this folder as the BaseUpdates folder ($UPDATE_FOLDER)
	-v			Print the version number and exit
	-z			Disable caching of the base image ($DISABLE_BASE_IMAGE_CACHING)
EOF
	if [ -z $1 ]; then
		exit 1;
	else
		exit $1
	fi
}

#<!------------------------ Phases ------------------------->

check_setup () {
	IFS=$'\n'
	
	# Check the language
	LANGUAGE_CODE_IS_VALID=false
	for LANGUAGE_CODE in $(/usr/sbin/installer -listiso | /usr/bin/tr "\t" "\n"); do
		if [ "$ISO_CODE" == "$LANGUAGE_CODE" ]; then
			LANGUAGE_CODE_IS_VALID=true
		fi
	done
	if [ $LANGUAGE_CODE_IS_VALID == false ]; then
		log "The ISO language code $ISO_CODE is not recognized by the Apple installer" error
		exit 1
	fi
	
	# If the ASR_OUPUT_FILE_NAME does not end in .dmg, add it
	if [ "`/bin/echo $ASR_OUPUT_FILE_NAME | /usr/bin/awk 'tolower($1) ~ /.*\.dmg$/ { print "true" }'`" != "true" ]; then
		ASR_OUPUT_FILE_NAME="$ASR_OUPUT_FILE_NAME.dmg"
	fi
	
	# make sure that the CONSOLE_LOG_LEVEL is one of the accepted values
	if [ "$CONSOLE_LOG_LEVEL" != "0" ] && [ "$CONSOLE_LOG_LEVEL" != "1" ] && [ "$CONSOLE_LOG_LEVEL" != "2" ] && [ "$CONSOLE_LOG_LEVEL" != "3" ] && [ "$CONSOLE_LOG_LEVEL" != "4" ]; then
		log "The conole log level must be an integer between 0 and 4" error
	fi
}

# check to make sure we are root
rootcheck() {
	# Root is required to run instadmg
	if [ $EUID != 0 ]; then
		log "You must run this utility using sudo or as root!" error-nolog
		exit 1
	fi
}

startup() {	
	IFS=' '
	FOLDER_LIST="INSTALLER_FOLDER UPDATE_FOLDER CUSTOM_FOLDER ASR_FOLDER BASE_IMAGE_CACHE LOG_FOLDER DMG_MOUNT_LOCATION"
	for FOLDER_ITEM in $FOLDER_LIST; do
		# sanitise the folder paths to make sure that they don't end in /
		if [ ${!FOLDER_ITEM: -1} == '/' ] && [ "${!FOLDER_ITEM}" != '/' ]; then
			THE_STR="${!FOLDER_ITEM}"
			eval $FOLDER_ITEM='${THE_STR: 0: $((${#THE_STR} - 1)) }'
		fi
		# check that all the things that should be folders are folders
		if [ ! -d "${!FOLDER_ITEM}" ]; then
			log "A required folder is missing or was not a folder: $FOLDER_ITEM: ${!FOLDER_ITEM}" error
			exit 1
		fi
	done
	
	# Create folder to enclose host mount points
	HOST_MOUNT_FOLDER=`/usr/bin/mktemp -d "$DMG_MOUNT_LOCATION/$MOUNT_FOLDER_TEMPLATE"`
	log "Host mount folder: $HOST_MOUNT_FOLDER" detail
	
	# Create mount point for the (read-only) target
	CURRENT_IMAGE_MOUNT=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
	log "Current image mount point: $CURRENT_IMAGE_MOUNT" detail
	
	# Decide the location for the shadow file to be attached to the target dmg
	SCRATCH_FILE_LOCATION="$HOST_MOUNT_FOLDER/`/usr/bin/uuidgen`.dmg"
	log "Shadow file location: $SCRATCH_FILE_LOCATION" detail
	
	# Get the MacOS X version information.
	OS_REV_MAJOR=`/usr/bin/sw_vers -productVersion | awk -F "." '{ print $2 }'`
	OS_REV_MINOR=`/usr/bin/sw_vers -productVersion | awk -F "." '{ print $3 }'`
	CPU_TYPE=`/usr/bin/arch`
}

# Look for the baseOS disk
find_base_os() {
	log "Finding main MacOS X installer disk" section
	
	INSTALLER_DISK_NAMES_ARRAY_LENGTH=${#ALLOWED_INSTALLER_DISK_NAMES[@]}
	
	IFS=$'\n'
	for IMAGE_FILE in $(/usr/bin/find "$INSTALLER_FOLDER" -iname '*.dmg'); do
		INDEX=0
		while [ "$INDEX" -lt "$INSTALLER_DISK_NAMES_ARRAY_LENGTH" ]; do
			if [ "$IMAGE_FILE" == "$INSTALLER_FOLDER/${ALLOWED_INSTALLER_DISK_NAMES[$INDEX]}" ]; then
				CURRENT_OS_INSTALL_FILE="$IMAGE_FILE"
				log "Found primary OS installer disk: $CURRENT_OS_INSTALL_FILE" information
				break
			fi
			let "INDEX = $INDEX + 1"
		done
	done
	
	if [ -z "$CURRENT_OS_INSTALL_FILE" ]; then
		log "Unable to find primary installer disk" error
		exit 1
	fi
}

# Look for and mount a cached image
mount_cached_image() {
	log "Looking for a Cached Image" section
	
	# figure out the name the filesystem should have
	
	# compatibility for old-style checksums (using colons)
	OLD_STYLE_BASE_IMAGE_CHECKSUM=''	# using colons
	
	BASE_IMAGE_CHECKSUM=`/usr/bin/hdiutil imageinfo "$CURRENT_OS_INSTALL_FILE" | /usr/bin/awk '/^Checksum Value:/ { print $3 }' | /usr/bin/sed 's/\\$//'`
	
	# sanity check
	if [ -z "$BASE_IMAGE_CHECKSUM" ]; then
		log "Unable to get checksum for image: $CURRENT_OS_INSTALL_FILE" error
		return
	fi
	
	INSTALLER_CHOICES_FILE=''
	if [ $OS_REV_MAJOR -gt 4 ] && [ -e "$INSTALLER_FOLDER/InstallerChoices.xml" ]; then
		INSTALLER_CHOICES_FILE="$INSTALLER_FOLDER/InstallerChoices.xml"
		
		INSTALLER_CHOICES_CHEKSUM=`/usr/bin/openssl dgst -sha1 "$INSTALLER_CHOICES_FILE" | awk 'sub(".*= ", "")'`
		OLD_STYLE_BASE_IMAGE_CHECKSUM="${BASE_IMAGE_CHECKSUM}:${INSTALLER_CHOICES_CHEKSUM}"
		BASE_IMAGE_CHECKSUM="${BASE_IMAGE_CHECKSUM}_${INSTALLER_CHOICES_CHEKSUM}"
	fi
	
	# look for the cached image, new style first
	if [ -e "${BASE_IMAGE_CACHE}/${BASE_IMAGE_CHECKSUM}.dmg" ]; then
		BASE_IMAGE_FILE="${BASE_IMAGE_CACHE}/${BASE_IMAGE_CHECKSUM}.dmg"
	
	elif [ -e "${BASE_IMAGE_CACHE}/${OLD_STYLE_BASE_IMAGE_CHECKSUM}.dmg" ]; then
		BASE_IMAGE_FILE="${BASE_IMAGE_CACHE}/${OLD_STYLE_BASE_IMAGE_CHECKSUM}.dmg"
	else
		log "No cached image found" information
		return
	fi
	
	# Mount the image and the shadow file
	log "Mounting the shadow file ($SCRATCH_FILE_LOCATION) onto the cached image ($BASE_IMAGE_FILE)" information
	/usr/bin/hdiutil mount "$BASE_IMAGE_FILE" -nobrowse -puppetstrings -owners on -mountpoint "$CURRENT_IMAGE_MOUNT" -shadow "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	# TODO: check to see if there was a problem
}

# Mount the OS source image and any supporting disks
mount_os_install() {
	log "Mounting Mac OS X installer image and supporting disks" section
	
	IFS=$'\n'
	for IMAGE_FILE in $(/usr/bin/find "$INSTALLER_FOLDER" -iname '*.dmg'); do
		if [ "$IMAGE_FILE" == "$CURRENT_OS_INSTALL_FILE" ]; then
			# primary installer disk
			
			# make sure that it is not already mounted
			IFS=$'\n'
			for HDIUTIL_LINE in $(/usr/bin/hdiutil info); do								
				if [ "$HDIUTIL_LINE" == '================================================' ]; then
					# this is the marker for a new section, so we need to clear things out
					IMAGE_LOCATION=""
					MOUNTED_IMAGES=""
			
				elif [ "`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk '/^image-path/'`" != "" ]; then
					IMAGE_LOCATION=`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk 'sub("^image-path[[:space:]]+:[[:space:]]+", "")'`
					
					# check the inodes to see if we are pointing at the same file
					if [ "`/bin/ls -Li "$IMAGE_LOCATION" 2>/dev/null | awk '{ print $1 }'`" != "`/bin/ls -Li "$IMAGE_FILE" | awk '{ print $1 }'`" ]; then
						# this is not the droid we are looking for
						IMAGE_LOCATION=""
						
						# if it is the same thing, then we let it through to get the mount point below
					fi
				elif [ "$IMAGE_LOCATION" != "" ] && [ "`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk '/\/dev\/.+[[:space:]]+Apple_HFS[[:space:]]+\//'`" != "" ]; then
					# find the mount point
					CURRENT_OS_INSTALL_MOUNT=`/bin/echo "$HDIUTIL_LINE" | /usr/bin/awk 'sub("/dev/.+[[:space:]]+Apple_HFS[[:space:]]+", "")'`
					# Here we are done!
					log "The main OS Installer Disk was already mounted at: $CURRENT_OS_INSTALL_MOUNT" warning
				fi
			done
			
			if [ -z "$CURRENT_OS_INSTALL_MOUNT" ]; then
				# mount the installer
				CURRENT_OS_INSTALL_MOUNT=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
				log "Mounting the main OS Installer Disk from: $IMAGE_FILE at: $CURRENT_OS_INSTALL_MOUNT" information
				/usr/bin/hdiutil mount "$IMAGE_FILE" -readonly -nobrowse -mountpoint "$CURRENT_OS_INSTALL_MOUNT" | (while read INPUT; do log $INPUT detail; done)
				CURRENT_OS_INSTALL_AUTOMOUNTED=true
				# TODO: check to see if there was a problem
			fi
			
			# check to see that the mount looks right
			if [ ! -d "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages" ]; then
				log "The main install disk was not sucessfully mounted!" error
				exit 1
			fi
		
		else
			# supporting disk
			SUPPORT_MOUNT_POINT=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
			log "Mounting a support disk from $INSTALLER_FOLDER/$IMAGE_FILE at $SUPPORT_MOUNT_POINT" information
			# note that we are allowing browsing of these files, so they will show up in the finder (and be found by the installer)
			/usr/bin/hdiutil mount "$INSTALLER_FOLDER/$IMAGE_FILE" -readonly -mountpoint "$SUPPORT_MOUNT_POINT" | (while read INPUT; do log $INPUT detail; done)
		fi
	done
	
	# check to make sure we are leaving something usefull
	if [ -z "$CURRENT_OS_INSTALL_MOUNT" ]; then
		log "No OS install disk or cached build was found" error
		exit 1
	fi
	
	log "Mac OS X installer image mounted" information
}

# setup and create the DMG.
create_and_mount_image() {
	log "Creating intermediary disk image" section
	
	if ["$CPU_TYPE" == "ppc" ]; then
		LAYOUT_TYPE="SPUD"
	elif [ "$CPU_TYPE" == "i386" ]; then
		LAYOUT_TYPE="GPTSPUD"
	else
		log "Unknown CPU type: $CPU_TYPE. Unable to continue" error
		exit 1
	fi
	
	/usr/bin/hdiutil create -size $DMG_SIZE -volname "$ASR_FILESYSTEM_NAME" -layout "$LAYOUT_TYPE" -type SPARSE -fs "HFS+" "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	/usr/bin/hdiutil mount "$SCRATCH_FILE_LOCATION" -noverify -nobrowse -mountpoint "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	if [ $? -ne 0 ]; then
		log "Failed to mount scratch image $SCRATCH_FILE_LOCATION mounted at $CURRENT_IMAGE_MOUNT" error
		exit 1
	fi
	
	log "Scratch image $SCRATCH_FILE_LOCATION mounted sucessfuly at $CURRENT_IMAGE_MOUNT" information
}

# Install from installation media to the DMG
install_system() {
	log "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" section
	
	INSTALLER_CHOICES_FILE=''
	
	# Check for InstallerChoices file, note we are excluding < 10.5
	if [ $OS_REV_MAJOR -gt 4 ]; then
		if [ -e "$INSTALLER_FOLDER/InstallerChoices.xml" ]; then
			INSTALLER_CHOICES_FILE="$INSTALLER_FOLDER/InstallerChoices.xml"
		fi
	else
		log "Running on Pre-10.5. InstallerChoices.xml files do not work" information
	fi
	
	OS_INSTALLER_PACKAGE=''
	if [ -e "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" ]; then
		OS_INSTALLER_PACKAGE="$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg"
	else
		log "The OS Install File is missing the OS Installer Package!" error
		exit 1
	fi
	
	if [ -z "$INSTALLER_CHOICES_FILE" ]; then
		log "Installing system from: $CURRENT_OS_INSTALL_MOUNT on to image at: $CURRENT_IMAGE_MOUNT using language code: $ISO_CODE" information
		/usr/sbin/installer -verbose -pkg "$OS_INSTALLER_PACKAGE" -target $CURRENT_IMAGE_MOUNT -lang $ISO_CODE | (while read INPUT; do log "$INPUT " detail; done)
	else
		log "Installing system from: $CURRENT_OS_INSTALL_MOUNT on to image at: $CURRENT_IMAGE_MOUNT using InstallerChoices file: $INSTALLER_CHOICES_FILE and language code: $ISO_CODE" information
		/usr/sbin/installer -verbose -applyChoiceChangesXML "$INSTALLER_CHOICES_FILE" -pkg "$OS_INSTALLER_PACKAGE" -target "$CURRENT_IMAGE_MOUNT" -lang "$ISO_CODE" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	log "Base OS installed" information
}

save_cached_image()	{
	# if we are at this point we need to close the image, move it to the cached folder
	log "Compacting and saving cached image to: $BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg" information
	
	# unmount the image
	/usr/bin/hdiutil eject "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	if [ ${?} -ne 0 ]; then
		# for some reason it did not un-mount, so we will try again with more force
		log "The image did not eject cleanly, so I will force it" information
		/usr/bin/hdiutil eject -force "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
		if [ ${?} -ne 0 ]; then
			log "Unable to unmount image to save cache image, unable to continue" error
			exit 1
		fi
	fi
	
	# move the image to the cached folder with the appropriate name
	BASE_IMAGE_FILE="$BASE_IMAGE_CACHE/$BASE_IMAGE_CHECKSUM.dmg"
	/bin/mv "$SCRATCH_FILE_LOCATION" "$BASE_IMAGE_FILE"
	if [ $? -ne 0 ]; then
		log "Unable to move the image to cache folder, unable to continue" error
		exit 1
	fi
	
	# NOTE: backing off this code for the moment... does not seem happy
	# compress the image and store it in the new location
	#/usr/bin/hdiutil convert -format UDZO -imagekey zlib-level=6 -o "$BASE_IMAGE_FILE" "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	
	# set the appropriate metadata on the file so that time-machine does not back it up
	if [ -x /usr/bin/xattr ]; then
		/usr/bin/xattr -w com.apple.metadata:com_apple_backup_excludeItem com.apple.backupd "$BASE_IMAGE_FILE"
	fi
}

# make any adjustments that need to be made before installing packages
prepare_image() {
	if [ $DISABLE_CHROOT == false ]; then
		# create a folder inside the chroot with the same path as the mount point pointing at root to fix some installer bugs
		/bin/mkdir -p "${CURRENT_IMAGE_MOUNT}${CURRENT_IMAGE_MOUNT}"
		/bin/rmdir "${CURRENT_IMAGE_MOUNT}${CURRENT_IMAGE_MOUNT}"
		/bin/ln -s / "${CURRENT_IMAGE_MOUNT}${CURRENT_IMAGE_MOUNT}"
		
		# make sure that the
		TARGET_TEMP_FOLDER="${CURRENT_IMAGE_MOUNT}${DMG_MOUNT_LOCATION}"
		/bin/mkdir -p "${CURRENT_IMAGE_MOUNT}${DMG_MOUNT_LOCATION}" # this should probably already exist
	fi
}

# install packages from a folder of folders (01, 02, 03...etc)
install_packages_from_folder() {
	SELECTED_FOLDER="$1"
	
	log "Beginning Update Installs from $SELECTED_FOLDER" section

	if [ "$SELECTED_FOLDER" == "" ]; then
		log "install_packages_from_folder called without folder" error
		exit 1;
	fi
	
	IFS=$'\n'
	for ORDERED_FOLDER in $(/bin/ls -A1 "$SELECTED_FOLDER" | /usr/bin/awk "/^[[:digit:]]+$/"); do
		TARGET="$SELECTED_FOLDER/$ORDERED_FOLDER"
		ORIGINAL_TARGET="$TARGET"
		DMG_MOUNT=''
		
		log "Working on folder $ORDERED_FOLDER" information
		
		# first resolve any chain of symlinks
		while [ -h "$TARGET" ]; do
			# look into this being a dmg
			NEW_LINK=`/usr/bin/readlink "$TARGET"`
			BASE_LINK=`/usr/bin/dirname "$TARGET"`
			TARGET="$BASE_LINK/$NEW_LINK"
		done
		
		# check for dmgs
		if [ -f "$TARGET" ]; then
			# see if it is a dmg. If it does not have a name, we can trust it is not a dmg
			DMG_INTERNAL_NAME=`/usr/bin/hdiutil imageinfo "$TARGET" 2>/dev/null | awk '/^\tName:/ && sub("\tName: ", "")'`
			if [ -z "$DMG_INTERNAL_NAME" ]; then
				# this is an unknown file type, so we need to bail
				log "Error: $ORIGINAL_TARGET pointed at $TARGET, which is an unknown file type (should be a dmg or a folder)" error
				exit 1
			else
				DMG_PATH="$TARGET"
				
				# mount in the host mount folder
				TARGET=`/usr/bin/mktemp -d "$HOST_MOUNT_FOLDER/$MOUNT_POINT_TEMPLATE"`
				DMG_MOUNT="$TARGET"
				log "	Mounting the package dmg: $DMG_INTERNAL_NAME ($ORIGINAL_TARGET) at: $TARGET" information
				/usr/bin/hdiutil mount "$DMG_PATH" -nobrowse -mountpoint "$TARGET" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
				if [ ${?} -ne 0 ]; then
					log "Unable to mount $DMG_INTERNAL_NAME ($DMG_PATH) at: $TARGET" error
					exit 1
				fi
			fi
		fi
		
		# If we are using a chroot jail copy the contents of the folder into the image
		TARGET_COPIED=false
		if [ $DISABLE_CHROOT == false ]; then
			# create a folder inside the HOST_MOUNT_FOLDER on the target
			OLD_TARGET="$TARGET"
			TARGET=`/usr/bin/mktemp -d "$TARGET_TEMP_FOLDER/$SOURCE_FOLDER_TEMPLATE"`
			log "	Copying folder $ORIGINAL_TARGET into the target at $TARGET" information
			/bin/cp -RH "$OLD_TARGET/" "$TARGET/" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
			
			TARGET_COPIED=true
		fi
		
		IFS=$'\n'	
		for UPDATE_PKG in $(/usr/bin/find -L "$TARGET" -maxdepth 1 -iname '*pkg' | /usr/bin/awk 'tolower() ~ /\.(m)?pkg/ && !/\/\._/'); do
			if [ -e "$TARGET/InstallerChoices.xml" ]; then
				CHOICES_FILE="InstallerChoices.xml"
				# TODO: better handle multiple pkg's and InstallerChoice files named for the file they should handle
			fi
			
			if [ $OS_REV_MAJOR -le 4 ]; then
				CHOICES_FILE="" # 10.4 can not use them
			fi			
			
			TARGET_FILE_NAME=`/usr/bin/basename "$UPDATE_PKG"`
			if [ "$ORIGINAL_TARGET" == "$TARGET" ]; then
				CONTAINER_PATH="$TARGET"
			else
				# probably a dmg installer
				CONTAINER_PATH=`/usr/bin/readlink "$ORIGINAL_TARGET"`
			fi
			
			if [ -z "$CHOICES_FILE" ]; then
				if [ $DISABLE_CHROOT == false ]; then
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH} (${ORDERED_FOLDER}) inside a chroot jail" information
					
					# note: the path to the update package needs to be absolute, not chroot relative, while the target needs to be chroot relative
					/usr/sbin/chroot "$CURRENT_IMAGE_MOUNT" /usr/sbin/installer -verbose -pkg "$TARGET/$TARGET_FILE_NAME" -target / | (while read INPUT; do log "$INPUT " detail; done)
				else
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH} (${ORDERED_FOLDER})" information
					/usr/sbin/installer -verbose -pkg "$TARGET/$TARGET_FILE_NAME" -target "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
				fi
			else
				if [ $DISABLE_CHROOT == false ]; then
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH}/${ORDERED_FOLDER} with XML Choices file: $CHOICES_FILE inside a chroot jail" information
					
					# note: the path to the update package needs to be absolute, not chroot relative, while the target needs to be chroot relative
					/usr/sbin/chroot "$CURRENT_IMAGE_MOUNT" /usr/sbin/installer -verbose -applyChoiceChangesXML "/private/tmp/$CHOICES_FILE" -pkg "$TARGET/$TARGET_FILE_NAME" -target / | (while read INPUT; do log "$INPUT " detail; done)
				else
					log "	Installing $TARGET_FILE_NAME from ${CONTAINER_PATH}  (${ORDERED_FOLDER}) with XML Choices file: $CHOICES_FILE" information
					/usr/sbin/installer -verbose -applyChoiceChangesXML "$TARGET/$CHOICES_FILE" -pkg "$TARGET/$TARGET_FILE_NAME" -target "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
				fi
			fi
		done
exit 1		
		# cleanup
		if [ ! -z "$DMG_PATH" ]; then
			log "Unmounting Package DMG: $DMG_MOUNT ($DMG_INTERNAL_NAME)" detail
			/usr/bin/hdiutil eject "$DMG_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
			if [ ${?} -ne 0 ]; then
				# for some reason it did not un-mount, so we will try again with more force
				log "The image did not eject cleanly, so I will force it" information
				/usr/bin/hdiutil eject -force "$DMG_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
			fi
			
			# remove up the mount point
			/bin/rmdir "$DMG_MOUNT" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
		fi
			
		if [ $TARGET_COPIED == true ]; then
			# delete the copied folder
			log "Removing the copied folder: $TARGET" detail
			/bin/rm -Rf "$TARGET" 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
		fi	

	done
}

# clean up some generic installer mistakes
clean_up_image() {
	log "Correcting some generic installer errors" section
	
	# find all the symlinks that are pointing to $CURRENT_IMAGE_MOUNT, and make them point at the "root"
	log "Correcting symlinks that point off the disk" information
	IFS=$'\n'
	for THIS_LINK in $(/usr/bin/find -x "$CURRENT_IMAGE_MOUNT" -type l); do
		if [ `/usr/bin/readlink "$THIS_LINK" | /usr/bin/grep -c "$CURRENT_IMAGE_MOUNT"` -gt 0 ]; then
		
			log "Correcting soft-link: $THIS_LINK" detail
			CORRECTED_LINK=`/usr/bin/readlink "$THIS_LINK" | /usr/bin/awk "sub(\"$CURRENT_IMAGE_MOUNT\", \"\") { print }"`
			
			/bin/rm "$THIS_LINK"
			/bin/ln -fs "$CORRECTED_LINK" "$THIS_LINK" | (while read INPUT; do log "$INPUT " detail; done)
		
		fi
	done
	
	# make sure that we have not left any open files behind
	log "Closing programs that have opened files on the disk" information
	/usr/sbin/lsof | /usr/bin/grep "$CURRENT_IMAGE_MOUNT/" | /usr/bin/awk '{ print $2 }' | /usr/bin/sort -u | /usr/bin/xargs /bin/kill 2>&1 | (while read INPUT; do log "$INPUT " detail; done)
	
	# Delete Extensions.mkext
	log "Deleting Extensions.mkext cache file" information
	/bin/rm -vf "$CURRENT_IMAGE_MOUNT/System/Library/Extensions.mkext" | (while read INPUT; do log "$INPUT " detail; done)
	
	# Delete items from /System/Caches and /Library/Caches
	log "Deleting cache files created during installations" information
	/bin/rm -vRf "$CURRENT_IMAGE_MOUNT/System/Library/Caches/*" | (while read INPUT; do log "$INPUT " detail; done)
	/bin/rm -vRf "$CURRENT_IMAGE_MOUNT/Library/Caches/*" | (while read INPUT; do log "$INPUT " detail; done)
	
	# Make sure that /tmp is empty
	/bin/rm -vRf "$CURRENT_IMAGE_MOUNT/private/var/tmp/*" | (while read INPUT; do log "$INPUT " detail; done)
	
}

# close up the DMG, compress and scan for restore
close_up_and_compress() {
	log "Creating the deployment DMG and scanning for ASR" section
	
	# We'll rename the newly installed system so that computers imaged with this will get the name
	log "Rename the deployment volume: $ASR_FILESYSTEM_NAME" information
	/usr/sbin/diskutil rename "$CURRENT_IMAGE_MOUNT" "$ASR_FILESYSTEM_NAME" | (while read INPUT; do log "$INPUT " detail; done)

	# Create a new, compessed, image from the intermediary one and scan for ASR.
	log "Create a read-only image"
	
	# unmount the image, then use convert to push it out to the desired place
	/usr/bin/hdiutil eject "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	if [ ${?} -ne 0 ]; then
		# for some reason it did not un-mount, so we will try again with more force
		log "The image did not eject cleanly, so I will force it" information
		/usr/bin/hdiutil eject -force "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
	if [ $DISABLE_BASE_IMAGE_CACHING == false ]; then
		# use the shadow file
		/usr/bin/hdiutil convert -ov -puppetstrings -format UDZO -imagekey zlib-level=6 -shadow "$SCRATCH_FILE_LOCATION" -o "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" "$BASE_IMAGE_FILE" | (while read INPUT; do log "$INPUT " detail; done)
	else
		# there is no shadow file to use, so the scratch file should be the one
		/usr/bin/hdiutil convert -ov -puppetstrings -format UDZO -imagekey zlib-level=6 -o "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done) 
	fi
	
	log "Scanning image for ASR: ${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" information
	/usr/sbin/asr imagescan --verbose --source "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" 2>&1  | (while read INPUT; do log "$INPUT " detail; done)
	log "ASR image scan complete" information

}

# restore DMG to test partition
restore_image() {
	log "Restoring ASR image to test partition" section
	/usr/sbin/asr --verbose --source "${ASR_FOLDER}/$ASR_OUPUT_FILE_NAME" --target "$ASR_TARGET_VOLUME" --erase --nocheck --noprompt | (while read INPUT; do log "$INPUT " detail; done)
	log "ASR image restored..." information
}

# set test partition to be the boot partition
set_boot_test() {
	log "Blessing test partition" section
	/usr/sbin/bless "--mount $CURRENT_IMAGE_MOUNT --setBoot" | (while read INPUT; do log "$INPUT " detail; done)
	log "Test partition blessed" information
}

# clean up
clean_up() {
	log "Cleaning up" section
	
	log "Ejecting images" information
	if [ -f "$CURRENT_IMAGE_MOUNT/System" ]; then
		/usr/bin/hdiutil eject "$CURRENT_IMAGE_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	if [ -d "$CURRENT_IMAGE_MOUNT" ] && [ "`/bin/ls $CURRENT_IMAGE_MOUNT | /usr/bin/grep -c .`" -eq 2 ]; then
		/bin/rmdir "$CURRENT_IMAGE_MOUNT"
	fi
	# TODO: close this image earlier
	if [ ! -z "$CURRENT_OS_INSTALL_MOUNT" ]; then
		/usr/bin/hdiutil eject "$CURRENT_OS_INSTALL_MOUNT" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	if [ $CURRENT_OS_INSTALL_AUTOMOUNTED == true ]; then
		/bin/rmdir "$CURRENT_OS_INSTALL_AUTOMOUNTED"
	fi
	
	log "Removing scratch DMG" 
	if [ ! -z "$SCRATCH_FILE_LOCATION" ] && [ -e "$SCRATCH_FILE_LOCATION" ]; then
		/bin/rm "$SCRATCH_FILE_LOCATION" | (while read INPUT; do log "$INPUT " detail; done)
	fi
	
}

# reboot the Mac
reboot() {
	log "Restarting" section
	/sbin/shutdown -r +1
}

#<!------------------------- Main -------------------------->

while getopts "b:c:d:hi:l:m:n:o:qrst:u:vz" opt
do
	case $opt in
		b ) INSTALLER_FOLDER="$OPTARG";;
		c ) CUSTOM_FOLDER="$OPTARG";;
		d ) CONSOLE_LOG_LEVEL="$OPTARG";;
		h ) usage 0;;
		i ) ISO_CODE="$OPTARG";;
		l ) LOG_FOLDER="$OPTARG";;
		m ) ASR_OUPUT_FILE_NAME="$OPTARG";;
		n ) ASR_FILESYSTEM_NAME="$OPTARG";;
		o ) ASR_FOLDER="$OPTARG";;
		q ) CONSOLE_LOG_LEVEL=0;;
		r ) DISABLE_CHROOT=true;;
		t ) DMG_MOUNT_LOCATION="$OPTARG";;
		u ) UPDATE_FOLDER="$OPTARG";;
		v ) version;;
		z ) DISABLE_BASE_IMAGE_CACHING=true;;
		\? ) usage;;
	esac
done

check_setup
rootcheck
startup

log "InstaDMG build initiated" section

find_base_os

if [ $DISABLE_BASE_IMAGE_CACHING == false ]; then
	mount_cached_image
fi

if [ -z "$CURRENT_IMAGE_MOUNT" ]; then
	mount_os_install
	create_and_mount_image
	install_system
	
	if [ $DISABLE_BASE_IMAGE_CACHING == false ]; then
		save_cached_image
		mount_cached_image
	fi
fi

prepare_image

install_packages_from_folder "$UPDATE_FOLDER"
install_packages_from_folder "$CUSTOM_FOLDER"

clean_up_image
close_up_and_compress
clean_up

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

log "InstaDMG Complete" section

exit 0
