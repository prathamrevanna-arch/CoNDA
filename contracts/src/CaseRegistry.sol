// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CaseRegistry {
    enum CaseStatus {
        OPEN,
        CHALLENGED,
        CLEARED,
        ESCALATED
    }

    struct CaseData {
        bytes32 evidenceHash;
        uint16 riskScore;
        uint8 status;
        address submitter;
        string groupRef;
    }

    uint256 public nextCaseId = 1;
    mapping(uint256 => CaseData) public cases;

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

    function openCase(
        bytes32 evidenceHash,
        uint16 riskScore,
        string calldata groupRef
    ) external returns (uint256 caseId) {
        caseId = nextCaseId++;
        cases[caseId] = CaseData({
            evidenceHash: evidenceHash,
            riskScore: riskScore,
            status: uint8(CaseStatus.OPEN),
            submitter: msg.sender,
            groupRef: groupRef
        });

        emit CaseOpened(caseId, evidenceHash, riskScore);
    }

    function submitChallenge(
        uint256 caseId,
        bytes32 policyCommitment,
        bytes calldata /* proof */
    ) external {
        require(caseId > 0 && caseId < nextCaseId, "Invalid caseId");
        cases[caseId].status = uint8(CaseStatus.CHALLENGED);

        emit ChallengeSubmitted(caseId, policyCommitment);
    }

    function resolveCase(
        uint256 caseId,
        uint8 status
    ) external {
        require(caseId > 0 && caseId < nextCaseId, "Invalid caseId");
        require(
            status == uint8(CaseStatus.CLEARED) || status == uint8(CaseStatus.ESCALATED),
            "Invalid status"
        );
        cases[caseId].status = status;

        emit CaseResolved(caseId, status);
    }

    function getCase(
        uint256 caseId
    ) external view returns (
        bytes32,
        uint16,
        uint8,
        address
    ) {
        require(caseId > 0 && caseId < nextCaseId, "Invalid caseId");
        CaseData storage c = cases[caseId];
        return (c.evidenceHash, c.riskScore, c.status, c.submitter);
    }
}