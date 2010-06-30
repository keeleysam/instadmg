//
//  improvedLog.h
//  InstallerChoicesHelper
//
//  Created by Karl Kuehn on 3/15/10.
//  Copyright 2010 Karl Kuehn. All rights reserved.
//

#include <asl.h>

// Inspired by Peter Hosey's series on asl_log
#ifndef ASL_KEY_FACILITY
#define ASL_KEY_FACILITY "Facility"
#endif

#ifdef DEBUG_MODE
#	define LOG_LEVEL_TO_PRINT ASL_LEVEL_DEBUG
#else
#	define LOG_LEVEL_TO_PRINT ASL_LEVEL_NOTICE
#endif

#define NSLog_level(log_level, format, ...) asl_log(NULL, NULL, log_level, "%s", [[NSString stringWithFormat:format, ##__VA_ARGS__] UTF8String]); if (log_level <= LOG_LEVEL_TO_PRINT) { if (log_level < ASL_LEVEL_WARNING) { fprintf(stderr, "Error: %s\n", [[NSString stringWithFormat:format, ##__VA_ARGS__] UTF8String]); } else { printf("%s%s%s\n", (ASL_LEVEL_WARNING + 1 < log_level ? "\t" : ""), (ASL_LEVEL_WARNING + 2 < log_level ? "\t" : ""), [[NSString stringWithFormat:format, ##__VA_ARGS__] UTF8String]); } }

#define NSLog_emerg(format, ...) NSLog_level(ASL_LEVEL_EMERG, format, ##__VA_ARGS__)
#define NSLog_alert(format, ...) NSLog_level(ASL_LEVEL_ALERT, format, ##__VA_ARGS__)
#define NSLog_crit(format, ...) NSLog_level(ASL_LEVEL_CRIT, format, ##__VA_ARGS__)
#define NSLog_error(format, ...) NSLog_level(ASL_LEVEL_ERR, format, ##__VA_ARGS__)
#define NSLog_warn(format, ...) NSLog_level(ASL_LEVEL_WARNING, format, ##__VA_ARGS__)
#define NSLog_notice(format, ...) NSLog_level(ASL_LEVEL_NOTICE, format, ##__VA_ARGS__)
#define NSLog_info(format, ...) NSLog_level(ASL_LEVEL_INFO, format, ##__VA_ARGS__)
#define NSLog_debug(format, ...) NSLog_level(ASL_LEVEL_DEBUG, format, ##__VA_ARGS__)
