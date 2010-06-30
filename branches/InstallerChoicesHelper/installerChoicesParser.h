//
//  InstallerChoicesHelperAppDelegate.h
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 9/30/09.
//  Copyright 2009 Karl Kuehn. All rights reserved.
//

#import <Cocoa/Cocoa.h>
#import "installerItem.h"
#import "improvedLog.h"

@interface installerChoicesParser : NSObject {
	
	NSString *			selectedPackagePath;
	NSString *			selectedPackageName;
	
	installerItem *		installerItemsTree;
	
	IBOutlet NSWindow *	displayWindow;
	
	NSThread *			_processingThread;
	BOOL				treeIsReady;		// marks that the GUI is ready, so things can be enabled
}

@property (assign) BOOL treeIsReady;

@property (retain) NSString * selectedPackagePath;
@property (retain) NSString * selectedPackageName;
@property (retain) installerItem * installerItemsTree;

@property (retain) IBOutlet NSWindow * displayWindow;

// called to set the package that we are working on
-(void) setSelectedPackagePath:(NSString *)path;

// called on a seperate thread to process the package in
-(void) parseInstallerChoicesAtPath:(NSString *)path;

// start the save process
-(IBAction) startSaveProcess:(id)sender;

// called to finally save the file out
-(void) saveInstallerChoicesFileFromSavePanel:(NSSavePanel *)savePanel returnCode:(int)returnCode conextInfo:(void *)contextInfo;

@end
