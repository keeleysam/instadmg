//
//  installerItem.m
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 10/3/09.
//  Copyright 2009 Karl Kuehn. All rights reserved.
//

#import "installerItem.h"
#import "improvedLog.h"

@implementation installerItem


@synthesize choiceTitle;
@synthesize choiceTitleColor;
@synthesize choiceDescription;
@synthesize choiceIdentifier;

// note: for choiceIsSelected both getter and setter are written out below
@synthesize choiceIsEnabled;
@synthesize choiceIsVisible;

@synthesize childItems;

// recursively create items from a plist
+ (installerItem *) newItemFromPlist:(NSDictionary *)plist {
	if (plist == nil) { 
		@throw [NSException exceptionWithName:@"instalerItemCreationException" reason:[NSString stringWithFormat:@"newItemFromPlist given empty plist value"] userInfo:nil];
	}
	if ([plist valueForKey:@"choiceIdentifier"] == nil) {
		@throw [NSException exceptionWithName:@"instalerItemCreationException" reason:[NSString stringWithFormat:@"newItemFromPlist given plist with no choiceIdentifier"] userInfo:nil];
	}
	
	NSLog_info(@"Processing item: %@", [plist valueForKey:@"choiceIdentifier"]);
	
	installerItem * newItem = [[installerItem alloc] init];
	
	NSArray * mandatoryKeys = [NSArray arrayWithObjects:@"choiceIdentifier", @"choiceIsEnabled", @"choiceIsSelected", @"choiceIsVisible", nil];
	NSArray * optionalKeys = [NSArray arrayWithObjects:@"choiceDescription", @"choiceTitle", nil];
	
	#pragma mark set the values
	for (NSString * thisKey in [mandatoryKeys arrayByAddingObjectsFromArray:optionalKeys]) {
		if ([plist valueForKey:thisKey] == nil && [mandatoryKeys containsObject:thisKey]) {
			[newItem release];
			@throw [NSException exceptionWithName:@"instalerItemCreationException" reason:[NSString stringWithFormat:@"missing %@ parameter", thisKey] userInfo:plist];
			
		} else if ([plist valueForKey:thisKey] != nil) {
			[newItem setValue:[plist valueForKey:thisKey] forKey:thisKey];
			NSLog_debug(@"Set value: '%@' for key: '%@'", [plist valueForKey:thisKey], thisKey);
		} else {
			NSLog_debug(@"No value for key: %@", thisKey);
		}
	}
	
	NSLog_info(@"Created item %@", [newItem choiceTitle]);
		
	#pragma mark create child items
	NSArray * workingChildren = [plist valueForKey:@"childItems"];
	if (workingChildren != nil) {
		newItem.childItems = [[NSMutableArray arrayWithCapacity:[workingChildren count]] retain]; // just make sure about this
		for (NSDictionary * childPlist in workingChildren) {
			installerItem * newSubItem = [installerItem newItemFromPlist:childPlist];
			[newItem.childItems addObject:newSubItem];
			[newSubItem release];
		}
	}
	
	return newItem;
}

- (NSString *) choiceTitle {
	if (choiceTitle == nil) {
		return [NSString stringWithFormat:@"<%@>", choiceIdentifier];
	}
	return choiceTitle;
}

- (NSColor *) choiceTitleColor {
	if (choiceTitle == nil) {
		return [NSColor lightGrayColor];
	}
	if (self.choiceIsVisible == NSOffState) {
		return [NSColor grayColor];
	}
	return [NSColor blackColor];
}

- (void) addChoicesDataToArray:(NSMutableArray *)choicesArray isRoot:(BOOL)isRoot {
	// we don't want the root item
	if (isRoot == FALSE) {
		NSDictionary * thisItemData = [NSDictionary dictionaryWithObjectsAndKeys:
			[NSNumber numberWithBool:choiceIsSelected], @"attributeSetting",
			@"selected", @"choiceAttribute",
			choiceIdentifier, @"choiceIdentifier",
			nil
		];
		
		[choicesArray addObject:thisItemData];
	}
	
	for (installerItem * thisItem in childItems) {
		[thisItem addChoicesDataToArray:choicesArray isRoot:FALSE];
	}
}

- (NSCellStateValue) choiceIsSelected {
	// if this is a leaf node, then we simply return the stored value
	if (childItems == nil || [childItems count] == 0) {
		return choiceIsSelected;
	}
	
	// since we are here this is a parent item, and its state is dependant on its children
	BOOL allOn = TRUE;
	BOOL allOff = TRUE;
	
	for (installerItem * thisItem in childItems) {
		if (thisItem.choiceIsSelected == NSOffState) {
			allOn = FALSE;
		} else if (thisItem.choiceIsSelected == NSOnState) {
			allOff = FALSE;
		} else {
			allOn = FALSE;
			allOff = FALSE;
		}

	}
	
	if (allOff == FALSE && allOn == FALSE) {
		return NSMixedState;
	} else if (allOff == TRUE) {
		return NSOffState;
	} else {
		return NSOnState;
	}
}

- (void) setChoiceIsSelected:(NSCellStateValue)newValue {
	NSLog(@"iuere");
	
	// if this is a leaf node, then store either NSOffState or NSOnState
	if (childItems == nil || [childItems count] == 0) {
		if (newValue == NSOffState) {
			choiceIsSelected = NSOffState;
		} else {
			choiceIsSelected = NSOnState;
		}
		return;
	}
	
	// here we have the more complicated case where we have to turn off, or on everything below us
	if (newValue == NSOffState) {
		[self recursivelySetChoiceIsSelected:NSOnState];
	} else {
		[self recursivelySetChoiceIsSelected:NSOffState];
	}

}

- (void) recursivelySetChoiceIsSelected:(NSCellStateValue)newValue {
	if (childItems == nil || [childItems count] == 0) {
		choiceIsSelected = newValue;
		return;
	}
	
	for (installerItem * thisItem in childItems) {
		[thisItem recursivelySetChoiceIsSelected:newValue];
	}
}

@end
