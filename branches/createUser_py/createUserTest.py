#!/usr/bin/env python

import os, unittest
from createUser import createUser

class userTests(unittest.TestCase):
	
	def setUp(self):
		self.createUserItem = createUser()
			
	def test_create(self):
		self.assert_(self.createUserItem is not None, "Unable to instantiate createUser")
		
	def test_dsclExists(self):
		self.assertTrue(self.createUserItem.pathToDscl() is not None, "The path to dscl is not defined.")
		self.assertTrue(os.path.isfile(self.createUserItem.pathToDscl()), "dscl was not where it was expected: %s" % self.createUserItem.pathToDscl())
	
	def test_dslocalExists(self):
		self.assertTrue(self.createUserItem.pathToDSLocal() is not None, "The path to DSLocal is not defined.")
		self.assertTrue(os.path.isdir(self.createUserItem.pathToDSLocal()), "dslocal was not where it was expected: %s" % self.createUserItem.pathToDSLocal())
	
	def test_getUserMethods(self):
		self.assertEqual(self.createUserItem.userNameAtUID(0), "root", "Can't get username for root's id")
		
		rootUserInfoByName = self.createUserItem.getUserInformationAtUserName("root")
		self.assertTrue(rootUserInfoByName is not None, "Can't get root's info by name properly, info is empty")
		self.assertTrue("dsAttrTypeStandard:RecordName" in rootUserInfoByName, "Can't get root's info by name properly, no RecordName")
		self.assertEqual(rootUserInfoByName["dsAttrTypeStandard:RecordName"], ["root"], "Can't get root's info by name properly, RecordName not 'root', was: %s" % rootUserInfoByName["dsAttrTypeStandard:RecordName"])
		
		rootUserInfoByID = self.createUserItem.getUserInformationAtUID(0)
		self.assertTrue(rootUserInfoByID is not None, "Can't get root's info by uid properly, info is empty")
		self.assertEqual(rootUserInfoByID, rootUserInfoByName, "The information returned by the id and name for root were not the same")
	
	def test_getUserMethods_negatives(self):
		self.assertEqual(self.createUserItem.userNameAtUID(-1), None, "Got a user for uid -1, this is wrong")
		
		rootUserInfoByName = self.createUserItem.getUserInformationAtUserName("users cant have spaces")
		self.assertTrue(rootUserInfoByName == None, "Got a user for uid -1, this is wrong")
	
	def test_nextAvalibleUID(self):
		firstRun = self.createUserItem.nextAvalibleUID()
		self.assertTrue(isinstance(firstRun, int), "Result of getNextAvalibleUID is not a number")
		
		# make sure that we get the same value if we run twice
		self.assertEqual(firstRun, self.createUserItem.nextAvalibleUID(), "Results of two sequential runs of nextAvalibleUID do not return the same value")
	
	def test_nextAvalibleUID_negatives(self):
		self.assertRaises(AssertionError, self.createUserItem.nextAvalibleUID, startNumber="not a number")
		self.assertRaises(AssertionError, self.createUserItem.nextAvalibleUID, startNumber=-1)
		self.assertRaises(AssertionError, self.createUserItem.nextAvalibleUID, endNumber="not a number")
		self.assertRaises(AssertionError, self.createUserItem.nextAvalibleUID, endNumber=-1)
		self.assertRaises(AssertionError, self.createUserItem.nextAvalibleUID, startNumber=4, endNumber=3)

class groupTests(unittest.TestCase):
	
	def setUp(self):
		self.createUserItem = createUser()
	
	def test_getGroupName(self):
		self.assertEqual("wheel", self.createUserItem.getGroupName(0), "getGroupName could not identify the group wheel by id")
		self.assertEqual("wheel", self.createUserItem.getGroupName("wheel"), "getGroupName could not identify the group wheel by name")
		self.assertEqual("wheel", self.createUserItem.getGroupName("ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000000"), "getGroupName could not identify the group wheel by uuid")
		
	def test_getGroupName_negatives(self):
		self.assertRaises(AssertionError, self.createUserItem.getGroupName, None)
		self.assertRaises(AssertionError, self.createUserItem.getGroupName, -1)
		self.assertRaises(AssertionError, self.createUserItem.getGroupName, [1, 2])
		
		self.assertEqual(None, self.createUserItem.getGroupName("names can't have spaces"), "getGroupName did not report an error for a bad name")
	
	def test_getUsersInGroup(self):
		wheelGroupMembers = ["FFFFEEEE-DDDD-CCCC-BBBB-AAAA00000000", "root"]
		self.assertEqual(wheelGroupMembers, self.createUserItem.getUsersInGroup(0), "getUsersInGroup did not return the normal members of wheel by gid")
		self.assertEqual(wheelGroupMembers, self.createUserItem.getUsersInGroup("wheel"), "getUsersInGroup did not return the normal members of wheel by name")
		self.assertEqual(wheelGroupMembers, self.createUserItem.getUsersInGroup("ABCDEFAB-CDEF-ABCD-EFAB-CDEF00000000"), "getUsersInGroup did not return the normal members of wheel by uuid")
	
	def test_getUsersInGroup_negatives(self):
		self.assertRaises(AssertionError, self.createUserItem.getUsersInGroup, None)
		self.assertRaises(AssertionError, self.createUserItem.getUsersInGroup, -1)
		self.assertRaises(AssertionError, self.createUserItem.getUsersInGroup, [1, 2])
		self.assertEqual(None, self.createUserItem.getUsersInGroup("group name should not have spaces"))
	
	def test_findNextAvalibleGID(self):
		self.assertTrue(self.createUserItem.findNextAvalibleGID() is not None)
	
	def test_findNextAvalibleGID_negative(self):
		self.assertRaises(AssertionError, self.createUserItem.findNextAvalibleGID, startNumber="not a number")
		self.assertRaises(AssertionError, self.createUserItem.findNextAvalibleGID, startNumber=-1)
		self.assertRaises(AssertionError, self.createUserItem.findNextAvalibleGID, endNumber="not a number")
		self.assertRaises(AssertionError, self.createUserItem.findNextAvalibleGID, endNumber=-1)
		self.assertRaises(AssertionError, self.createUserItem.findNextAvalibleGID, startNumber=4, endNumber=3)
	
if __name__ == "__main__":
	unittest.main()
	
	