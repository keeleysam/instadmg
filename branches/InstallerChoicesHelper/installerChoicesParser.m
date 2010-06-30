//
//  InstallerChoicesHelperAppDelegate.m
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 9/30/09.
//  Copyright 2009 Karl Kuehn. All rights reserved.
//

#import "installerChoicesParser.h"
#import "improvedLog.h"

@implementation installerChoicesParser


@synthesize selectedPackagePath; // note: the setter is written out below
@synthesize selectedPackageName;
@synthesize installerItemsTree;
@synthesize treeIsReady;
@synthesize displayWindow;

-(void)setSelectedPackagePath:(NSString *)path {
	
	// grab the name and set the path
	self.selectedPackageName = [path lastPathComponent];
	selectedPackagePath = path;
	
	// empty out the display area
	self.installerItemsTree = nil;
	self.treeIsReady = FALSE;
	
	// spawn a thread to get the installerChoices data
	if (_processingThread != nil) {
		if (![_processingThread isFinished]) {
			[_processingThread cancel];
		}
		[_processingThread release];
	}
	_processingThread = [[[NSThread alloc] initWithTarget:self selector:@selector(parseInstallerChoicesAtPath:) object:path] retain];
	[_processingThread start];
}

-(void)parseInstallerChoicesAtPath:(NSString *)path {
	// process the installer at path to get the installerChoices data
	
	NSAutoreleasePool * pool = [[NSAutoreleasePool alloc] init];
	
	NSLog_info(@"Starting to process file at: %@", path);
	
	// get the data from installer
	NSPipe * listTaskData = [NSPipe pipe];
	NSTask * installerListTask = [[NSTask alloc] init];
	[installerListTask setLaunchPath:@"/usr/sbin/installer"];
	NSArray * arguments = [NSArray arrayWithObjects:@"-showChoicesXML", @"-pkg", path, @"-target", @"/", nil];
	[installerListTask setArguments:arguments];
	NSLog_debug(@"About to process NSTask: %@ %@", @"/usr/sbin/installer", [arguments componentsJoinedByString:@" "]);
	[installerListTask setStandardOutput:listTaskData];
	[installerListTask launch];
	[installerListTask waitUntilExit];
	if ([installerListTask terminationStatus] != 0) {
		[installerListTask release];
		@throw [NSException exceptionWithName:@"instalerItemReadException" reason:[NSString stringWithFormat:@"unable to get choices from mpkg: %@", path] userInfo:nil];
	}
	[installerListTask release];
	
	NSLog_debug(@"Finished NSTask operation on: %@", path);
	
	// process the plist into objects
	NSError * plistError;
	NSPropertyListFormat plistFormat = NSPropertyListXMLFormat_v1_0;
	NSArray * installerList = [NSPropertyListSerialization propertyListWithData:[[listTaskData fileHandleForReading] readDataToEndOfFile] options:0 format:&plistFormat error:&plistError];
	
	// process the generic objects into installerChoices
	installerItem * thisInstallerItem = [installerItem newItemFromPlist:[installerList objectAtIndex:0]];
	
	self.installerItemsTree = thisInstallerItem;
	self.treeIsReady = TRUE;
	
	[pool release];
}

-(IBAction) startSaveProcess:(id)sender {
	
	NSString * targetFileExtension = @"installerChoices";
	
	// setup options for the save panel
	NSSavePanel * mySavePanel = [NSSavePanel savePanel];
	[mySavePanel setAllowedFileTypes:[NSArray arrayWithObjects:targetFileExtension, nil]];
	[mySavePanel setAllowsOtherFileTypes:YES];
	// ToDo: default this to somewhere usefull
	
	NSString * suggestedFileName = [NSString stringWithFormat:@"%@", [selectedPackageName stringByDeletingPathExtension]];
	
	[mySavePanel beginSheetForDirectory:NSHomeDirectory() file:suggestedFileName modalForWindow:displayWindow modalDelegate:self didEndSelector:@selector(saveInstallerChoicesFileFromSavePanel:returnCode:conextInfo:) contextInfo:NULL];
	
	NSLog_debug(@"Began model save sheet");
}

-(void) saveInstallerChoicesFileFromSavePanel:(NSSavePanel *)savePanel returnCode:(int)returnCode conextInfo:(void *)contextInfo {
	
	if (returnCode != NSOKButton) {
		// the user hit cancel
		NSLog_debug(@"User canceled model save sheet");
		return;
	}
	
	NSURL * path = [savePanel URL];
	
	NSLog_info(@"Starting to save choices file at: %@", [path path]);
	
	// collect the data from the tree
	NSMutableArray * installerChoicesResults = [NSMutableArray arrayWithCapacity:10];
	[installerItemsTree addChoicesDataToArray:installerChoicesResults isRoot:TRUE];
	
	if ([NSPropertyListSerialization propertyList:installerChoicesResults isValidForFormat:NSPropertyListXMLFormat_v1_0] == NO) {
		@throw [NSException exceptionWithName:@"instalerChoicesWriteException" reason:@"unable to seralize installer choices results" userInfo:nil];
	}
	
	NSString * errorString = nil;
	NSData * installerChoicesNSData = [NSPropertyListSerialization dataFromPropertyList:installerChoicesResults format:NSPropertyListXMLFormat_v1_0 errorDescription:&errorString];
	if (errorString != nil) {
		@throw [NSException exceptionWithName:@"instalerChoicesWriteException" reason:[NSString stringWithFormat:@"unable to seralize installer choices results, got error: %@", errorString] userInfo:nil];
	}
	NSLog_debug(@"Created NSData for choices file");
	
	// write out the data
	NSError * writeError = nil;
	[installerChoicesNSData writeToURL:path options:NSAtomicWrite error:&writeError];
	if (writeError != nil) {
		NSLog(@"here");
		@throw [NSException exceptionWithName:@"instalerChoicesWriteException" reason:[NSString stringWithFormat:@"Got an error while writing: %@", [writeError localizedFailureReason]] userInfo:nil];
	}
	
	NSLog_info(@"Wrote out choices file to: %@", path);
}
@end
