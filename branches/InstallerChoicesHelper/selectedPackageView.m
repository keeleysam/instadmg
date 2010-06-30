//
//  selectedPackageView.m
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 10/3/09.
//  Copyright 2009 Karl Kuehn. All rights reserved.
//

#import "selectedPackageView.h"
#import "booleanToStringTransformer.h"

@implementation selectedPackageView

@synthesize cachedFilePath;
@synthesize cachedFileType;

+(void) initialize {
	[super initialize];
	[self initialiseValueTransformers];
}

+(void) initialiseValueTransformers {
	booleanToStringTransformer * myTransformer = [[[booleanToStringTransformer alloc] init] autorelease];
	[booleanToStringTransformer setValueTransformer:myTransformer forName:@"booleanToStringTransformer"];
}

- (void) awakeFromNib {
	[self registerForDraggedTypes: [NSArray arrayWithObjects: NSFilenamesPboardType, nil]];
}

- (NSDragOperation) draggingEntered:(id <NSDraggingInfo>)sender {
	NSPasteboard * pasteboard = [sender draggingPasteboard];
	
	// set the default responce (no)
	NSDragOperation responce = NSDragOperationNone;
	
	if ([[pasteboard types] containsObject:NSFilenamesPboardType]) {
		
		NSString * filePath = [[pasteboard propertyListForType:NSFilenamesPboardType]objectAtIndex:0];
		NSLog(@"new file at path: %@", filePath);
		
		NSString * fileType = nil;
		NSString * openingApp = nil; // we actually will not use this information
		
		if ([[NSWorkspace sharedWorkspace] getInfoForFile:filePath application:&openingApp type:&fileType] == NO) {
			// not something we can deal with
			return responce;
		}
		NSLog(@"File type was: %@", fileType);
		
		if ([fileType compare:@"mpkg"] == NSOrderedSame) {
			// this is the sort we are looking for
			//responce = [sender draggingSourceOperationMask];
			responce = NSDragOperationGeneric;
			
			highlighted = TRUE;
			[self display];
			
			// grab the info while we have it
			self.cachedFilePath = filePath;
			self.cachedFileType = fileType;
		}
	}
	return responce;
}

- (void)draggingExited:sender {
	highlighted = FALSE;
	[self display];
}

- (void)drawRect:(NSRect)rect {
	if (highlighted) {
		[super drawRect:rect];
		[NSGraphicsContext saveGraphicsState];
		NSRect focusRingFrame = rect;
		NSSetFocusRingStyle(NSFocusRingTypeExterior);
		[[NSBezierPath bezierPathWithRect: NSInsetRect(focusRingFrame,4,4)] stroke];
		[NSGraphicsContext restoreGraphicsState];
	} else {
		[super drawRect:rect];
	}
}

- (BOOL) prepareForDragOperation:(id)sender {
	return YES;
}

- (void) concludeDragOperation:(id)sender {
	
	// set the image
	NSImage * selectedFileIcon = [[NSWorkspace sharedWorkspace] iconForFileType:cachedFileType];
	if (selectedFileIcon == nil) {
		@throw [NSException exceptionWithName:@"instalerItemCreationException" reason:[NSString stringWithFormat:@"unable to get icon for file type: %@", cachedFileType] userInfo:nil];

	}
	[self setImage:selectedFileIcon];
	
	highlighted = FALSE;
	[self display];
	
	[choicesParser setSelectedPackagePath:cachedFilePath];
}

@end
