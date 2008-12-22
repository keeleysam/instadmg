#!/bin/bash

#
# instadmg - script to automate creating ASR disk images
#

#
#  Joel Rennich - mactroll@afp548.com - SFO -> ORD
#  Josh Wisenbaker - macshome@afp548.com - CLT -> LAX (Among many others...)
#

# Version 1.0

#
# some defaults to get us started
#

# Set the creation date in a variable so it's consistant during execution.
CREATE_DATE=`date +%y-%m-%d`

# Put images of your install DVDs in here
INSTALLER_FOLDER=./BaseOS

# Put naked Apple pkg updates in here. Prefix a number to order them.
UPDATE_FOLDER=./AppleUpdates

# Put naked custom pkg installers here. Prefix a number to order them.
CUSTOM_FOLDER=./CustomPKG

# This is the final ASR destination for the image.
ASR_FOLDER=./ASR_Output

# This is where DMG scratch is done. Set this to whatever you want.
DMG_SCRATCH=./DMG_Scratch

# This string is the root of the scratch image name.
DMG_BASE_NAME="InstaDMG"

# This string is the root filesystem name for the ASR image to be restored.
DMG_FS_NAME="InstaDMG"

# Default log location.
LOG_FOLDER=./Logs

# Default log names. The PKG log is a more consise history of what was installed.
LOG_FILE=$LOG_FOLDER/$CREATE_DATE.log
PKG_LOG=$LOG_FOLDER/$CREATE_DATE.pkg.log

# Default scratch image size. It should not need adjustment.
DMG_SIZE=300g

# ASR target volume. Make sure you set it to the correct thing! In a future release this, and most variables, will be a getopts parameter.
ASR_TARGET_VOLUME=/Volumes/foo

#
# Some shell variables we need
#

export COMMAND_LINE_INSTALL=1

#
# Now for the meat
#

# check to make sure we are root, can't do these things otherwise

check_root() {
    if [ `whoami` != "root" ]
    then
        /bin/echo "you need to be root to do this"
        exit 0;
    fi
}

# setup and create the DMG. Uncomment and comment the reformatting based on your platform. This will be automated in a future release.

create_and_mount_image() {
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/echo "Creating disk image" >> $LOG_FILE
	[ -e ${DMG_BASE_NAME}.${CREATE_DATE}.sparseimage ] && $CREATE_DATE		
	/usr/bin/hdiutil create -size $DMG_SIZE -type SPARSE -fs HFS+ $DMG_SCRATCH/${DMG_BASE_NAME}.${CREATE_DATE}
	CURRENT_IMAGE_MOUNT_DEV=`/usr/bin/hdiutil mount $DMG_SCRATCH/$DMG_BASE_NAME.$CREATE_DATE.sparseimage | /usr/bin/head -n 1 |  /usr/bin/awk '{ print $1 }'`
	/bin/echo "Image mounted at $CURRENT_IMAGE_MOUNT_DEV" >> $LOG_FILE
	
# Format the DMG so that the Installer will like it (Intel Mac)
	/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_FS_NAME GPTFormat $CURRENT_IMAGE_MOUNT_DEV
	CURRENT_IMAGE_MOUNT=/Volumes/$DMG_FS_NAME
	
# Format the DMG so that the Installer will like it (PPC Mac)
#	/usr/sbin/diskutil eraseDisk "Journaled HFS+" $DMG_FS_NAME bootable $CURRENT_IMAGE_MOUNT_DEV
#	CURRENT_IMAGE_MOUNT=/Volumes/$DMG_FS_NAME
}

# Mount the OS source image.
# If you have some wacky disk name then change this as needed.

mount_os_install() {
	/bin/ls -1 $INSTALLER_FOLDER | while read i
	do
	 /usr/bin/hdiutil mount "$INSTALLER_FOLDER/$i"
	done
	if [ -d /Volumes/Mac\ OS\ X\ Install\ Disc\ 1 ]
		then
		CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install Disc 1"
		else
		CURRENT_OS_INSTALL_MOUNT="/Volumes/Mac OS X Install DVD"
	fi
}

# Install from installation media to the DMG
# The default is to install with english as the primary.
# Change to your ISO code as needed.

install_system() {
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/echo $CREATE_DATE >> $PKG_LOG
	/bin/echo "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" >> $LOG_FILE
	/bin/echo "Beginning Installation from $CURRENT_OS_INSTALL_MOUNT" >> $PKG_LOG
	/usr/sbin/installer -verbose -pkg "$CURRENT_OS_INSTALL_MOUNT/System/Installation/Packages/OSInstall.mpkg" -target $CURRENT_IMAGE_MOUNT -lang en >> $LOG_FILE
}

# install the updates to the DMG
install_updates() {
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/echo $CREATE_DATE >> $PKG_LOG
	/bin/echo "Beginning Update Installs from $UPDATE_FOLDER" >> $LOG_FILE
	/bin/echo "Beginning Update Installs from $UPDATE_FOLDER" >> $PKG_LOG
	
	for UPDATE_PKG in `ls $UPDATE_FOLDER`
		do
		/usr/sbin/installer -verbose -pkg ${UPDATE_FOLDER}/${UPDATE_PKG} -target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
		/bin/echo "Installed $UPDATE_PKG" >> $PKG_LOG
	done
}

# install the custom pieces to the DMG
install_custom() {
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/echo $CREATE_DATE >> $PKG_LOG
	/bin/echo "Beginning Update Installs from $CUSTOM_FOLDER" >> $LOG_FILE
	/bin/echo "Beginning Update Installs from $CUSTOM_FOLDER" >> $PKG_LOG
	
	for CUSTOM_PKG in `ls $CUSTOM_FOLDER`
		do
		/usr/sbin/installer -verbose -pkg ${CUSTOM_FOLDER}/${CUSTOM_PKG} -target $CURRENT_IMAGE_MOUNT >> $LOG_FILE
		/bin/echo "Installed $CUSTOM_PKG" >> $PKG_LOG
	done
}

# close up the DMG, compress and scan for restore
close_up_and_compress() {
	/bin/echo $CREATE_DATE >> $LOG_FILE
	/bin/echo "Creating the deployment DMG and scanning for ASR" >> $LOG_FILE
	
	# We'll rename the newly installed system to make it easier to work with later
	/bin/echo "Rename the deployment volume" >> $LOG_FILE
	/usr/sbin/diskutil rename $CURRENT_IMAGE_MOUNT OS-Build-${CREATE_DATE}
	CURRENT_IMAGE_MOUNT=/Volumes/OS-Build-${CREATE_DATE}
	
	/bin/echo "Build a new image from folder..." >> $LOG_FILE
	/usr/bin/hdiutil create -format UDZO -imagekey zlib-level=6 -srcfolder $CURRENT_IMAGE_MOUNT  ${ASR_FOLDER}/${CREATE_DATE} >> $LOG_FILE
	/usr/sbin/diskutil eject $CURRENT_IMAGE_MOUNT_DEV
	/bin/echo "Scanning image for ASR" >> $LOG_FILE
	/bin/echo "Image to scan is ${ASR_FOLDER}/${CREATE_DATE}.dmg" >> $LOG_FILE
	/usr/sbin/asr imagescan --source ${ASR_FOLDER}/${CREATE_DATE}.dmg >> $LOG_FILE
}

# restore DMG to test partition
restore_image() {
	/usr/sbin/asr --source ${ASR_FOLDER}/${CREATE_DATE}.dmg --target $ASR_TARGET_VOLUME --erase --nocheck --noprompt >> $LOG_FILE
}

# set test partition to be the boot partition
set_boot_test() {
	/usr/sbin/bless --mount /Volumes/OS-Build-${CURRENT_DATE} --setBoot
}

# clean up
clean_up() {
	/bin/rm ./DMG_Scratch/*
}

# reboot the Mac
reboot() {
	/sbin/shutdown -r +1
}


# Call the handlers as needed to make it all happen.
create_and_mount_image
mount_os_install
install_system
install_updates
install_custom
close_up_and_compress
clean_up

# Automated restore options. Be careful as these can destroy data.
# restore_image
# set_boot_test
# reboot

exit 0