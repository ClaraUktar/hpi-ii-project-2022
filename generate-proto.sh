#!/bin/bash

protoc --proto_path=proto --python_out=build/gen proto/bakdata/corporate/v1/corporate.proto
protoc --proto_path=proto --python_out=build/gen proto/bakdata/corporate/v1/patent.proto

protoc --proto_path=proto --python_out=build/gen proto/bakdata/corporate/v2/company.proto
protoc --proto_path=proto --python_out=build/gen proto/bakdata/corporate/v2/cleaned_company.proto
