//
//  booleanToStringTransformer.m
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 3/20/10.
//  Copyright 2010 __MyCompanyName__. All rights reserved.
//

#import "booleanToStringTransformer.h"


@implementation booleanToStringTransformer

+ (Class)transformedValueClass {
	return [NSString class];
}

+ (BOOL)allowsReverseTransformation {
	return NO;
}

- (id)transformedValue:(id)value {
	if (value == nil) {
		return nil;
	}
	
	if ([value intValue] > 0) {
		return [NSString stringWithString:@"✓"];
	}
	return [NSString stringWithString:@""];
}

@end
