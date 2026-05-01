// Copyright (c) 2026 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#include "brave/ios/browser/brave_shields/farbling_javascript_feature.h"

namespace brave_shields {

namespace {
constexpr char kScriptName[] = "farbling";
}  // namespace

FarblingJavaScriptFeature::FarblingJavaScriptFeature()
    : JavaScriptFeature(
          web::ContentWorld::kPageContentWorld,
          {web::JavaScriptFeature::FeatureScript::CreateWithFilename(
              kScriptName,
              web::JavaScriptFeature::FeatureScript::InjectionTime::
                  kDocumentStart,
              web::JavaScriptFeature::FeatureScript::TargetFrames::kAllFrames,
              web::JavaScriptFeature::FeatureScript::ReinjectionBehavior::
                  kInjectOncePerWindow)}) {}

FarblingJavaScriptFeature::~FarblingJavaScriptFeature() = default;

// static
FarblingJavaScriptFeature* FarblingJavaScriptFeature::GetInstance() {
  static base::NoDestructor<FarblingJavaScriptFeature> instance;
  return instance.get();
}

}  // namespace brave_shields
