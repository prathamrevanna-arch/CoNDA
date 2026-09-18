// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/CaseRegistry.sol";

contract DeployScript is Script {
    function run() external returns (CaseRegistry registry) {
        vm.startBroadcast();
        registry = new CaseRegistry();
        vm.stopBroadcast();
    }
}