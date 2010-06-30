//
//  selectedPackageView.h
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 10/3/09.
//  Copyright 2009 Karl Kuehn. All rights reserved.
//

#import <Cocoa/Cocoa.h>
#include "installerChoicesParser.h"
#import "improvedLog.h"

@interface selectedPackageView : NSImageView {
	
	// cache items (so we don't do work twice)
	NSString * cachedFilePath;
	NSString * cachedFileType; // should only ever be mpkg
	
	BOOL highlighted;
	
	IBOutlet installerChoicesParser * choicesParser;
}

@property (retain) IBOutlet NSString * cachedFilePath;
@property (retain) IBOutlet NSString * cachedFileType;

+(void)initialiseValueTransformers;

@end
