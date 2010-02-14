#!/usr/bin/env python

import sys, os, re
import subprocess, Foundation


class createUser:
	
	pathToRoot = "/"
	relativePathTodsclPath = "usr/bin/dscl"
	relativePathToDSLocal = "private/var/db/dslocal/nodes/Default"
	
	def pathToDscl(self):
		return os.path.join(self.pathToRoot, self.relativePathTodsclPath)
	
	def pathToDSLocal(self):
		return os.path.join(self.pathToRoot, self.relativePathToDSLocal)
	
	def dsclCommandPrefix(self):
		''' The common first section of the dscl commands '''
		return [self.pathToDscl(), "-plist", "-f", self.pathToDSLocal(), "localonly"] # note: the -plist will not affect anything but -read commands
	
	
	userNameFromIDSearch = re.compile("^(?P<userName>\S+)\s+dsAttrTypeNative:uid = \(\n\s+\d+\n\)")
	def userNameAtUID(self, uid):
		assert isinstance(uid, int), "UID must be an integer"
		
		dsclCommand = self.dsclCommandPrefix() + ["-search", "/Local/Default/Users", "uid", str(uid)]
		dsclProcess = subprocess.Popen(dsclCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		if dsclProcess.wait() != 0:
			raise Exception("dscl user search failed from command: %s\n\twith error: %s" % (" ".join(dsclCommand), dsclProcess.stderr.read()))
		
		dsclOutput = dsclProcess.stdout.read()
		
		serchResult = self.userNameFromIDSearch.match(dsclOutput)
		if serchResult == None:
			return None
		else:
			return serchResult.group("userName")
	
	def getUserInformationAtUserName(self, userName):
		assert isinstance(userName, str), "UserName must be a string"
		
		dsclCommand = self.dsclCommandPrefix() + ["-read", "/Local/Default/Users/" + userName]
		dsclProcess = subprocess.Popen(dsclCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		dsclOutput = dsclProcess.stdout.read()
		if dsclOutput == None or dsclOutput.strip() == "":
			return None
		
		plistNSData = Foundation.NSString.stringWithString_(dsclOutput).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			raise Exception("Unable to read plist from dscl uid search result.\nGot error: %s\nFrom data: %s" %(error, dsclOutput))
		
		return plistData
	
	def getUserInformationAtUID(self, uid):
		assert isinstance(uid, int), "UID must be an integer"
		
		userName = self.userNameAtUID(uid)
		if userName == None:
			return None
		else:
			return self.getUserInformationAtUserName(userName)
		
	
	def nextAvalibleUID(self, startNumber=501, endNumber=600):
		assert isinstance(startNumber, int) and startNumber >= 0, "startNumber must be a positive integer"
		assert isinstance(endNumber, int) and endNumber >= 0 and startNumber <= endNumber, "endNumber must be a positive integer and at least startNumber (%i)" % startNumber
		
		for uid in range(startNumber, endNumber + 1):
			if self.userNameAtUID(uid) == None:
				return uid
		
		return None
	
	#--------------------------Group functions--------------------------
	
	groupNameFromIDSearch = re.compile("^(?P<groupName>\S+)\s+dsAttrTypeNative:gid = \(\n\s+\d+\n\)")
	groupNameFromUUIDSearch = re.compile("^(?P<groupName>\S+)\s+GeneratedUID = \(\n\s+\S+\n\)")
	def getGroupName(self, groupIdentifier):
		assert groupIdentifier is not None, "getGroupName given an empty value"
		assert isinstance(groupIdentifier, int) or isinstance(groupIdentifier, str)
		
		''' This method atempts to find a group based on the identifier given, which can be a GID, group name, or group's UUID '''
		
		if isinstance(groupIdentifier, int):
			assert groupIdentifier >= 0, "GIDs can only be positive"
			# this can only be a GID
			
			dsclCommand = self.dsclCommandPrefix() + ["-search", "/Local/Default/Groups", "gid", str(groupIdentifier)]
			dsclProcess = subprocess.Popen(dsclCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			
			if dsclProcess.wait() != 0:
				raise Exception("dscl group id search failed from command: %s\n\twith error: %s" % (" ".join(dsclCommand), dsclProcess.stderr.read()))
			
			dsclOutput = dsclProcess.stdout.read()
			if dsclOutput == None or dsclOutput.strip() == "":
					return None
			
			serchResult = self.groupNameFromIDSearch.match(dsclOutput)
			if serchResult == None:
				return None
			else:
				return serchResult.group("groupName")
		
		elif isinstance(groupIdentifier, str):
			# this could be either a UUID, or more likely a group name
			
			# try a group name
			dsclCommand = self.dsclCommandPrefix() + ["-read", "/Local/Default/Groups/" + groupIdentifier]
			dsclProcess = subprocess.Popen(dsclCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			
			if dsclProcess.wait() == 0:
				# just getting a non-error response tell us this is correct
				return groupIdentifier
				
			else:
				# try this as a UUID
				dsclCommand = self.dsclCommandPrefix() + ["-search", "/Local/Default/Groups", "GeneratedUID", groupIdentifier]
				dsclProcess = subprocess.Popen(dsclCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
								
				dsclOutput = dsclProcess.stdout.read()
				if dsclOutput == None or dsclOutput.strip() == "":
					return None
				
				serchResult = self.groupNameFromUUIDSearch.match(dsclOutput)
				if serchResult == None:
					return None
				else:
					return serchResult.group("groupName")
				
	
	def getUsersInGroup(self, groupIdentifier):
		assert groupIdentifier is not None, "getGroupName given an empty value"
		assert isinstance(groupIdentifier, int) or isinstance(groupIdentifier, str)
		
		groupName = self.getGroupName(groupIdentifier)
		if groupName is None:
			return None
		
		dsclCommand = self.dsclCommandPrefix() + ["-read", "/Local/Default/Groups/" + groupName]
		dsclProcess = subprocess.Popen(dsclCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		dsclOutput = dsclProcess.stdout.read()
		if dsclOutput == None or dsclOutput.strip() == "":
			return None
		
		plistNSData = Foundation.NSString.stringWithString_(dsclOutput).dataUsingEncoding_(Foundation.NSUTF8StringEncoding)
		plistData, format, error = Foundation.NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(plistNSData, Foundation.NSPropertyListImmutable, None, None)
		if error:
			raise Exception("Unable to read plist from dscl uid search result.\nGot error: %s\nFrom data: %s" %(error, dsclOutput))
		
		assert "dsAttrTypeStandard:GroupMembers" in plistData, "getUsersInGroup got a plist missing any dsAttrTypeStandard:GroupMembers entry"
		assert "dsAttrTypeStandard:GroupMembership" in plistData, "getUsersInGroup got a plist missing any dsAttrTypeStandard:GroupMembership entry"
		
		# the [:] entries are to force a conversion to a python array from the NSCArray
		return plistData["dsAttrTypeStandard:GroupMembers"][:] + plistData["dsAttrTypeStandard:GroupMembership"][:]
		
	def findNextAvalibleGID(self, startNumber=501, endNumber=600):
		assert isinstance(startNumber, int) and startNumber >= 0, "startNumber must be a positive integer"
		assert isinstance(endNumber, int) and endNumber >= 0 and startNumber <= endNumber, "endNumber must be a positive integer and at least startNumber (%i)" % startNumber
		
		for gid in range(startNumber, endNumber + 1):
			if self.getGroupName(gid) == None:
				return gid
		
		return None
	
	def isUserInGroup(self, user, group, recursive=False):
		assert isinstance(groupIdentifier, int) or isinstance(groupIdentifier, str)
		# TODO: impliment the recursive part
	

