//
//  installerItem.h
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 10/3/09.
//  Copyright 2009 Karl Kuehn. All rights reserved.
//

#import <Cocoa/Cocoa.h>
#import "improvedLog.h"

@interface installerItem : NSObject {
	
	NSString * choiceTitle;
	NSString * choiceDescription;
	NSString * choiceIdentifier;
	
	NSCellStateValue choiceIsSelected;
	NSCellStateValue choiceIsEnabled;
	NSCellStateValue choiceIsVisible;
	
	NSMutableArray * childItems;
	
}

@property (retain) NSString * choiceTitle;
@property (readonly) NSColor * choiceTitleColor;
@property (retain) NSString * choiceDescription;
@property (retain) NSString * choiceIdentifier;

@property (readonly) NSCellStateValue choiceIsSelected;
@property (assign) NSCellStateValue choiceIsEnabled;
@property (readonly) NSCellStateValue choiceIsVisible;

@property (retain) NSMutableArray * childItems;

// recursively create items from a plist
+ (installerItem *) newItemFromPlist:(NSDictionary *)plist;

// recursivly add the choices data to an Array that is passed in at the root
- (void) addChoicesDataToArray:(NSMutableArray *)choicesArray isRoot:(BOOL)isRoot;

// recursively change the choice
- (void) recursivelySetChoiceIsSelected:(NSCellStateValue)newValue;


@end
