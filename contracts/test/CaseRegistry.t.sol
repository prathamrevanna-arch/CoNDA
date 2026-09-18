// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/CaseRegistry.sol";

contract CaseRegistryTest is Test {
    CaseRegistry public registry;

    bytes32 constant EVIDENCE_HASH = keccak256("evidence_123");
    bytes32 constant POLICY_COMMITMENT = keccak256("policy_123");
    uint16 constant RISK_SCORE = 85;
    string constant GROUP_REF = "A2,A3";

    event CaseOpened(
        uint256 indexed caseId,
        bytes32 evidenceHash,
        uint16 riskScore
    );

    event ChallengeSubmitted(
        uint256 indexed caseId,
        bytes32 policyCommitment
    );

    event CaseResolved(
        uint256 indexed caseId,
        uint8 status
    );

    function setUp() public {
        registry = new CaseRegistry();
    }

    function test_OpenCase() public {
        vm.expectEmit(true, false, false, true);
        emit CaseOpened(1, EVIDENCE_HASH, RISK_SCORE);

        uint256 caseId = registry.openCase(EVIDENCE_HASH, RISK_SCORE, GROUP_REF);
        assertEq(caseId, 1);

        (bytes32 evHash, uint16 risk, uint8 status, address submitter) = registry.getCase(caseId);
        assertEq(evHash, EVIDENCE_HASH);
        assertEq(risk, RISK_SCORE);
        assertEq(status, 0); // OPEN
        assertEq(submitter, address(this));
    }

    function test_SubmitChallenge() public {
        uint256 caseId = registry.openCase(EVIDENCE_HASH, RISK_SCORE, GROUP_REF);

        vm.expectEmit(true, false, false, true);
        emit ChallengeSubmitted(caseId, POLICY_COMMITMENT);

        bytes memory proof = "mock_proof";
        registry.submitChallenge(caseId, POLICY_COMMITMENT, proof);

        (, , uint8 status, ) = registry.getCase(caseId);
        assertEq(status, 1); // CHALLENGED
    }

    function test_ResolveCase_Cleared() public {
        uint256 caseId = registry.openCase(EVIDENCE_HASH, RISK_SCORE, GROUP_REF);
        registry.submitChallenge(caseId, POLICY_COMMITMENT, "proof");

        vm.expectEmit(true, false, false, true);
        emit CaseResolved(caseId, 2); // CLEARED

        registry.resolveCase(caseId, 2);

        (, , uint8 status, ) = registry.getCase(caseId);
        assertEq(status, 2); // CLEARED
    }

    function test_ResolveCase_Escalated() public {
        uint256 caseId = registry.openCase(EVIDENCE_HASH, RISK_SCORE, GROUP_REF);

        vm.expectEmit(true, false, false, true);
        emit CaseResolved(caseId, 3); // ESCALATED

        registry.resolveCase(caseId, 3);

        (, , uint8 status, ) = registry.getCase(caseId);
        assertEq(status, 3); // ESCALATED
    }

    function test_RevertWhen_InvalidCaseId_GetCase() public {
        vm.expectRevert("Invalid caseId");
        registry.getCase(0);

        vm.expectRevert("Invalid caseId");
        registry.getCase(999);
    }

    function test_RevertWhen_InvalidCaseId_SubmitChallenge() public {
        vm.expectRevert("Invalid caseId");
        registry.submitChallenge(999, POLICY_COMMITMENT, "proof");
    }

    function test_RevertWhen_InvalidCaseId_ResolveCase() public {
        vm.expectRevert("Invalid caseId");
        registry.resolveCase(999, 2);
    }

    function test_RevertWhen_InvalidStatus_ResolveCase() public {
        uint256 caseId = registry.openCase(EVIDENCE_HASH, RISK_SCORE, GROUP_REF);

        vm.expectRevert("Invalid status");
        registry.resolveCase(caseId, 0);

        vm.expectRevert("Invalid status");
        registry.resolveCase(caseId, 1);

        vm.expectRevert("Invalid status");
        registry.resolveCase(caseId, 4);
    }
}