#!/usr/bin/python

import os, unittest, re

import dmg
from .commonTestConfiguration		import	getFirstOSInstallerDiscPath
from .container						import	container
from .pathHelpers					import	pathInsideFolder, normalizePath
from .tempFolderManager				import	tempFolderManager

class dmg_test(unittest.TestCase):
	
	def test_installerImages(self):
		'''Test the class with a dmg from the BaseOS or InstallerDisks folders'''
		
		testItemPath = getFirstOSInstallerDiscPath()
		
		# -- simple tests
		
		# confirm that the class picks up on it as a dmg
		testItem = container(testItemPath)
		self.assertEqual(testItem.getContainerType(), 'dmg', 'Expected containerType for "%s" to be "dmg", but got: %s' % (testItemPath, testItem.getContainerType()))
		
		# chack that it gives back the correct storeage path
		self.assertEqual(normalizePath(testItemPath, followSymlink=True), testItem.getStoragePath(), 'Item did not return the correct storage path (%s) but rather: %s' % (testItemPath, testItem.getStoragePath()))
		
		# check to see if the item is mounted
		self.assertEqual(testItem.getMountPoint(), None, 'Did not expect the item (%s) to be mounted, but it was at: %s' % (testItemPath, testItem.getMountPoint()))
		
		# try mounting the item without any options
		testItem.mount()
		self.assertTrue(testItem.getMountPoint() is not None, 'Mounting the item (%s) with no options did not get a mount point' % testItemPath)
		
		# test that the content looks like it is there
		actualMountPoint = testItem.getMountPoint()
		self.assertTrue(os.path.ismount(actualMountPoint), 'After mounting the item (%s) with no options, the reported mount point (%s) was not a mount' % (testItemPath, actualMountPoint))
		self.assertTrue(os.path.isdir(os.path.join(actualMountPoint, 'System')), 'After mounting the item (%s) with no options, the System folder was not in the mount point')
		
		# check that getWorkingPath gets the mounted volume
		workingPath = testItem.getWorkingPath()
		self.assertTrue(workingPath is not None, 'The working path returned from a mounted item (%s) was None' % testItemPath)
		self.assertEqual(workingPath, actualMountPoint, 'The working path returned from a mounted item (%s) was "%s" rather than the expected "%s"' % (testItemPath, workingPath, actualMountPoint))
		
		# unmount the volume
		testItem.unmount()
		actualMountPoint = testItem.getMountPoint()
		self.assertTrue(actualMountPoint is None, 'After unmounting the item (%s) there was still a mount point: %s' % (testItemPath, actualMountPoint))
		
		# check that getWorkingPath remounts the item
		workingPath = testItem.getWorkingPath()
		self.assertTrue(workingPath is not None, 'The working path returned from a unmounted item (%s) was None' % testItemPath)
		self.assertTrue(os.path.ismount(workingPath), 'The working path returned from a unmounted item (%s) was not a mount point' % testItemPath)
		testItem.unmount()
		
		# -- mountpoint tests
		
		targetMountPoint = tempFolderManager.getNewMountPoint()
		actualMountPoint = testItem.mount(mountPoint=targetMountPoint)
		self.assertEqual(targetMountPoint, actualMountPoint, 'Mounting the item (%s) at a specified mount point (%s) returned %s' % (testItemPath, targetMountPoint, actualMountPoint))
		self.assertEqual(targetMountPoint, testItem.getMountPoint(), 'Mounting the item (%s) at a specified mount point (%s) resulted in a mount point of %s' % (testItemPath, targetMountPoint, testItem.getMountPoint()))
		
		# -- getWorkingPath with withinFolder tests
		
		# note: we already have an image mounted at a know point from the previous tests
		newMountArea = tempFolderManager.getNewTempFolder()
		newMountPoint = testItem.getWorkingPath(withinFolder=newMountArea)
		self.assertTrue(newMountPoint is not None, 'After changing the mount point with getWorkingPath(withinFolder=value) the returned value was None')
		self.assertTrue(os.path.ismount(newMountPoint), 'After changing the mount point with getWorkingPath(withinFolder=value) the returned value (%s) was not a mount point' % newMountPoint)
		self.assertTrue(pathInsideFolder(newMountPoint, newMountArea), 'After changing the mount point with getWorkingPath(withinFolder=value) the returned value (%s) was not inside expected directory (%s)' % (newMountPoint, newMountArea))
		
		testItem.unmount()
		
		# -- singleton tests - make sure the same item is only created once
		duplicateItem = container(testItemPath)
		self.assertEqual(duplicateItem, testItem, 'When feeding the same dmg (%s) into container twice, got seperate items')
		
		# shadow file - make sure that an item with a shadow file is not registered as the same item without a shadow file
		itemWithShadowFile = container(testItemPath, shadowFile=True)
		self.assertNotEqual(itemWithShadowFile, duplicateItem, 'An item created with a shadow file returned the same object as one created without a shadow file')
		
		# different shadow file - should be yet another item
		secondItemWithShadowFile = container(testItemPath, shadowFile=True)
		self.assertNotEqual(secondItemWithShadowFile, duplicateItem, 'The second item created with a shadow file returned the same object as one created without a shadow file')
		self.assertNotEqual(itemWithShadowFile, secondItemWithShadowFile, 'The second item created with a shadow file returned the same object with the first shadow file')
		
		# mountpoint test - feed container the mountpoint and make sure it comes back with the same item
		mountPointItem = container(duplicateItem.getWorkingPath())
		self.assertEqual(duplicateItem, mountPointItem, 'When fed the mount point of an item container should have returned the same item, but it did not')

		# -- getMacOSInformation
		
		macOSInformation = duplicateItem.getMacOSInformation()
		self.assertTrue(macOSInformation is not None, 'Could not get the MacOS information from the disc: ' + testItemPath)
		
		# macOSType
		self.assertTrue(macOSInformation['macOSType'] is not None, 'Could not get the macOSType from the disc: ' + testItemPath)
		
		# macOSVersion
		self.assertTrue(macOSInformation['macOSVersion'] is not None, 'Could not get the macOSVersion from the disc: ' + testItemPath)
		
		# macOSBuild
		self.assertTrue(macOSInformation['macOSBuild'] is not None, 'Could not get the macOSBuild from the disc: ' + testItemPath)
		
		# macOSInstallerDisc
		self.assertTrue(macOSInformation['macOSInstallerDisc'] is not None, 'Could not get the macOSBuild from the disc: ' + testItemPath)
		self.assertTrue(macOSInformation['macOSInstallerDisc'] is True, 'The disc did not evaluate as an installer disc as expected: ' + testItemPath)
		
		# -- getTopLevelItems
		
		# test with an open dmg
		
		duplicateItem.mount() # should be a no-op
		listOfItems = os.listdir(duplicateItem.getMountPoint())
		
		self.assertEqual(listOfItems, duplicateItem.getTopLevelItems(), 'Expected results of getTopLevelItems on mounted dmg "%s" to be "%s", but got: %s' % (testItemPath, listOfItems, duplicateItem.getTopLevelItems()))
		
		# close the dmg and try again
		
		duplicateItem.unmount()
		self.assertEqual(listOfItems, duplicateItem.getTopLevelItems(), 'Expected results of getTopLevelItems on mounted dmg "%s" to be "%s", but got: %s' % (testItemPath, listOfItems, duplicateItem.getTopLevelItems()))
		self.assertFalse(duplicateItem.isMounted(), 'The dmg was not auto-unmounted after checking for the top level items')
