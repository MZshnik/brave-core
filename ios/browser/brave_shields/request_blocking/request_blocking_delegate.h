// Copyright (c) 2026 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#ifdef __cplusplus
#include "brave/components/brave_shields/ios/common/shields_settings.mojom.objc.h"
#else
#import "shields_settings.mojom.objc.h"
#endif

@protocol RequestBlockingDelegate <NSObject>

@required

/**
 * Determines the AdBlockMode for the given URL.
 *
 * @param url The URL to check for ad blocking.
 * @return The AdBlockMode for the given URL.
 */
- (BraveShieldsAdBlockMode)adblockMode:(NSURL*)url;

/**
 * Determines whether a specific resource should be blocked.
 *
 * @param requestURL The URL of the requested resource.
 * @param sourceURL The URL of the page that initiated the request.
 * @param resourceType A string indicating the type of resource (e.g., "image",
 * "script", "stylesheet").
 * @param adblockMode The ad blocking mode to apply.
 * @return YES if the resource should be blocked, NO otherwise.
 */
- (BOOL)shouldBlockRequestURL:(NSURL*)requestURL
                    sourceURL:(NSURL*)sourceURL
                 resourceType:(NSString*)resourceType
                  adblockMode:(BraveShieldsAdBlockMode)adblockMode
    NS_SWIFT_NAME(shouldBlock(requestURL:sourceURL:resourceType:adblockMode:));

@end
