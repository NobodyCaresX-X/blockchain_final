// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Crowdfunding {
    enum ProjectStatus {
        Active,
        Successful,
        Failed
    }

    // 阶段点 - 作业要求的里程碑（达到目标%发放资金）
    struct Stage {
        string description;
        uint256 completionThresholdBps; // 0-10000表示0%-100%
        uint256 releaseBps;
        bool completed;
        bool released;
    }

    // 里程碑 - 发起者承诺的回报（达标线+承诺+时间）
    struct Reward {
        uint256 fundingThreshold;    // 达标金额（wei）
        string promiseText;          // 发起者承诺内容
        uint256 expectedMonth;       // 预计实现时间（月，从创建时算起）
        uint256 backersCount;        // 支持者数量
    }

    // 月度支持
    struct MonthlySupport {
        uint256 monthlyAmount;      // 每月支持金额（wei）
        uint256 nextBillingTime;     // 下次扣款时间
        bool active;                 // 是否激活
    }

    struct Project {
        uint256 id;
        address creator;
        string name;
        string description;
        uint256 goal;               // 基础目标金额（wei）
        uint256 deadline;
        uint256 pledged;            // 已承诺金额
        uint256 balance;            // 合约余额
        uint256 totalWithdrawn;     // 已提现金额
        uint256 totalRefunded;       // 已退款金额
        ProjectStatus status;
        bool ended;
        bool creatorWithdrawn;
        bool hasStages;             // 是否开启阶段点
        bool hasMonthlySupport;     // 是否开启月度支持
        uint256 donorCount;
    }

    uint256 public nextProjectId = 1;
    uint256 public constant BPS = 10_000;
    uint256 public constant MONTH = 30 days; // 约一个月
    
    // 计算下一个每月1日0:0:00 UTC的时间戳
    function _getNextMonthFirstDay() private view returns (uint256) {
        uint256 currentTimestamp = block.timestamp;
        uint256 daysSince1970 = currentTimestamp / 86400;
        
        // 计算年份
        uint256 year = 1970;
        uint256 daysAcc = 0;
        for (uint256 y = 1970; y < 2100; y++) {
            uint256 yearDays = 365;
            if (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)) {
                yearDays = 366;
            }
            if (daysAcc + yearDays > daysSince1970) {
                year = y;
                break;
            }
            daysAcc += yearDays;
        }
        
        // 计算当前年的天数
        uint256 daysInCurrentYear = daysSince1970 - daysAcc;
        
        // 月份天数
        uint256[12] memory monthDays = [uint256(31), 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) {
            monthDays[1] = 29;
        }
        
        // 计算当前月份
        uint256 currentMonth = 1;
        uint256 daysInMonths = 0;
        for (uint256 m = 0; m < 12; m++) {
            if (daysInCurrentYear < daysInMonths + monthDays[m]) {
                currentMonth = m + 1;
                break;
            }
            daysInMonths += monthDays[m];
        }
        
        // 计算下月1日的天数
        uint256 nextMonth = currentMonth == 12 ? 1 : currentMonth + 1;
        
        // 计算从1970到下月1日的天数
        uint256 daysToNextMonth;
        if (currentMonth == 12) {
            // 下年是1月
            daysToNextMonth = daysAcc + 365;
            if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) {
                daysToNextMonth = daysAcc + 366;
            }
        } else {
            daysToNextMonth = daysAcc + daysInMonths + monthDays[currentMonth - 1];
        }
        
        return daysToNextMonth * 86400;
    }

    mapping(uint256 => Project) private projects;
    mapping(uint256 => address[]) private projectDonors;
    mapping(uint256 => mapping(address => uint256)) private donations;
    mapping(uint256 => mapping(address => bool)) private earlySupporters;
    mapping(uint256 => mapping(address => bool)) private monthlySupporters; // 细水长流标签
    mapping(uint256 => Stage[]) private projectStages;
    mapping(uint256 => Reward[]) private projectRewards;
    mapping(uint256 => mapping(address => MonthlySupport)) private monthlySupports;
    uint256[] private projectIds;

    event ProjectCreated(uint256 indexed projectId, address indexed creator, string name, uint256 goal, uint256 deadline, bool hasStages, bool hasMonthlySupport);
    event DonationReceived(uint256 indexed projectId, address indexed donor, uint256 amount, uint256 totalPledged);
    event ProjectFinished(uint256 indexed projectId, ProjectStatus status, uint256 pledged, uint256 goal);
    event CreatorWithdrawal(uint256 indexed projectId, address indexed creator, uint256 amount);
    event DonationRefunded(uint256 indexed projectId, address indexed donor, uint256 amount);
    event StageCreated(uint256 indexed projectId, uint256 indexed stageIndex, string description, uint256 completionThresholdBps, uint256 releaseBps);
    event StageCompleted(uint256 indexed projectId, uint256 indexed stageIndex);
    event StageReleased(uint256 indexed projectId, uint256 indexed stageIndex, uint256 amount);
    event MonthlySupportStarted(uint256 indexed projectId, address indexed donor, uint256 monthlyAmount);
    event MonthlySupportStopped(uint256 indexed projectId, address indexed donor);
    event MonthlySupportCharged(uint256 indexed projectId, address indexed donor, uint256 amount);

    modifier onlyCreator(uint256 projectId) {
        require(projects[projectId].creator == msg.sender, "only creator");
        _;
    }

    modifier projectExists(uint256 projectId) {
        require(projects[projectId].id != 0, "project not found");
        _;
    }

    function createProject(
        string calldata name,
        string calldata description,
        uint256 goal,
        uint256 deadline,
        bool hasStages,                              // 是否开启阶段点
        string[] calldata stageDescriptions,           // 阶段点描述
        uint256[] calldata stageThresholdsBps,        // 阶段点达标比例（0-10000）
        uint256[] calldata stageReleaseBps,           // 阶段点释放比例
        bool hasMonthlySupport,                      // 是否开启月度支持
        uint256[] calldata rewardThresholds,           // 里程碑达标线
        string[] calldata rewardPromises,              // 里程碑承诺内容
        uint256[] calldata rewardMonths               // 里程碑预计实现时间（月）
    ) external returns (uint256) {
        require(goal > 0, "goal must be > 0");
        require(deadline > block.timestamp, "deadline must be in the future");

        // 验证阶段点参数
        if (hasStages) {
            require(
                stageDescriptions.length == stageThresholdsBps.length &&
                stageDescriptions.length == stageReleaseBps.length,
                "stage length mismatch"
            );
            // 阶段点进度限制：0-100%（均不含）
            for (uint256 i = 0; i < stageThresholdsBps.length; i++) {
                require(stageThresholdsBps[i] > 0 && stageThresholdsBps[i] < BPS, "stage threshold must be 0-100%");
                require(stageReleaseBps[i] > 0 && stageReleaseBps[i] <= BPS, "stage release must be 0-100%");
            }
        }

        // 验证里程碑参数
        if (rewardThresholds.length > 0) {
            require(
                rewardThresholds.length == rewardPromises.length &&
                rewardThresholds.length == rewardMonths.length,
                "reward length mismatch"
            );
            // 里程碑达标线必须大于0且必须超过目标（里程碑是超产目标）
            for (uint256 i = 0; i < rewardThresholds.length; i++) {
                require(rewardThresholds[i] > goal, "reward threshold must exceed goal");
            }
        }

        uint256 projectId = nextProjectId;
        nextProjectId += 1;

        Project storage project = projects[projectId];
        project.id = projectId;
        project.creator = msg.sender;
        project.name = name;
        project.description = description;
        project.goal = goal;
        project.deadline = deadline;
        project.status = ProjectStatus.Active;
        project.hasStages = hasStages;
        project.hasMonthlySupport = hasMonthlySupport;

        projectIds.push(projectId);

        // 创建阶段点
        for (uint256 i = 0; i < stageDescriptions.length; i++) {
            projectStages[projectId].push(Stage({
                description: stageDescriptions[i],
                completionThresholdBps: stageThresholdsBps[i],
                releaseBps: stageReleaseBps[i],
                completed: false,
                released: false
            }));
            emit StageCreated(projectId, i, stageDescriptions[i], stageThresholdsBps[i], stageReleaseBps[i]);
        }

        // 创建里程碑（发起者承诺）
        for (uint256 i = 0; i < rewardThresholds.length; i++) {
            projectRewards[projectId].push(Reward({
                fundingThreshold: rewardThresholds[i],
                promiseText: rewardPromises[i],
                expectedMonth: rewardMonths[i],
                backersCount: 0
            }));
        }

        emit ProjectCreated(projectId, msg.sender, name, goal, deadline, hasStages, hasMonthlySupport);
        return projectId;
    }

    function donate(uint256 projectId) external payable projectExists(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Active, "project not active");
        require(block.timestamp < project.deadline, "project ended");
        require(msg.value > 0, "donation must be > 0");

        _recordDonation(projectId, msg.sender, msg.value);
    }

    function donateFor(uint256 projectId, address donor) external payable projectExists(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Active, "project not active");
        require(block.timestamp < project.deadline, "project ended");
        require(msg.value > 0, "donation must be > 0");

        _recordDonation(projectId, donor, msg.value);
    }

    function _recordDonation(uint256 projectId, address donor, uint256 amount) private {
        Project storage project = projects[projectId];

        if (donations[projectId][donor] == 0) {
            projectDonors[projectId].push(donor);
            project.donorCount += 1;
            if (project.donorCount <= 10) {
                earlySupporters[projectId][donor] = true;
            }
        }

        donations[projectId][donor] += amount;
        project.pledged += amount;
        project.balance += amount;

        // 更新里程碑支持者数量
        _updateRewardBackers(projectId, project.pledged);

        emit DonationReceived(projectId, donor, amount, project.pledged);
    }

    function _updateRewardBackers(uint256 projectId, uint256 currentPledged) private {
        Reward[] storage rewards = projectRewards[projectId];
        for (uint256 i = 0; i < rewards.length; i++) {
            if (currentPledged >= rewards[i].fundingThreshold) {
                rewards[i].backersCount += 1;
            }
        }
    }

    // 开始月度支持
    function startMonthlySupport(uint256 projectId, uint256 monthlyAmount) external payable projectExists(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Active, "project not active");
        require(project.hasMonthlySupport, "monthly support not enabled");
        require(monthlyAmount > 0, "monthly amount must be > 0");

        // 首次扣款作为激活费用（立即执行）
        require(msg.value >= monthlyAmount, "must prepay first month");

        MonthlySupport storage support = monthlySupports[projectId][msg.sender];
        support.monthlyAmount = monthlyAmount;
        // 设置下次扣款时间为下月1日0:0:00 UTC
        support.nextBillingTime = _getNextMonthFirstDay();
        support.active = true;

        monthlySupporters[projectId][msg.sender] = true;
        // 首次扣款立即执行
        _recordDonation(projectId, msg.sender, monthlyAmount);

        emit MonthlySupportStarted(projectId, msg.sender, monthlyAmount);
    }

    // 停止月度支持
    function stopMonthlySupport(uint256 projectId) external projectExists(projectId) {
        MonthlySupport storage support = monthlySupports[projectId][msg.sender];
        require(support.active, "not active");

        support.active = false;
        monthlySupporters[projectId][msg.sender] = false;

        emit MonthlySupportStopped(projectId, msg.sender);
    }

    // 自动扣款（月度支持）- 每月1日0:0:00执行
    function chargeMonthlySupport(uint256 projectId) external projectExists(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Active, "project not active");

        MonthlySupport storage support = monthlySupports[projectId][msg.sender];
        require(support.active, "not active");
        require(block.timestamp >= support.nextBillingTime, "not time yet");

        // 检查是否超出目标且未开启阶段点
        uint256 excessAmount = 0;
        if (!project.hasStages && project.pledged > project.goal) {
            excessAmount = project.pledged - project.goal;
        }

        uint256 amountToCharge = support.monthlyAmount;
        if (excessAmount > 0 && amountToCharge > excessAmount) {
            amountToCharge = excessAmount;
        }

        // 设置下次扣款时间为再下月1日0:0:00 UTC
        uint256 currentNextBilling = support.nextBillingTime;
        // 简单计算：加上约30天（平均每月天数）
        support.nextBillingTime = currentNextBilling + 30 days;

        _recordDonation(projectId, msg.sender, amountToCharge);

        emit MonthlySupportCharged(projectId, msg.sender, amountToCharge);
    }

    // 自动检查并结束所有到期的项目
    function checkAndFinishExpired() external {
        for (uint256 i = 1; i <= nextProjectId; i++) {
            if (_projectExists(i)) {
                Project storage project = projects[i];
                if (!project.ended && block.timestamp >= project.deadline) {
                    // 自动结束项目
                    project.ended = true;
                    
                    if (project.pledged >= project.goal) {
                        project.status = ProjectStatus.Successful;
                        if (project.hasStages) {
                            _calculateProportionalRelease(i);
                        }
                    } else {
                        project.status = ProjectStatus.Failed;
                        if (project.hasStages) {
                            _calculateProportionalRefund(i);
                        }
                    }
                    
                    emit ProjectFinished(i, project.status, project.pledged, project.goal);
                }
            }
        }
    }
    
    // 检查项目是否存在（内部函数）
    function _projectExists(uint256 projectId) private view returns (bool) {
        return projectId > 0 && projectId < nextProjectId;
    }

    function finishProject(uint256 projectId) external projectExists(projectId) {
        Project storage project = projects[projectId];
        require(!project.ended, "already ended");
        require(block.timestamp >= project.deadline, "deadline not reached");

        project.ended = true;

        if (project.pledged >= project.goal) {
            project.status = ProjectStatus.Successful;
            // 如果开启了阶段点，按比例计算可发放金额
            if (project.hasStages) {
                _calculateProportionalRelease(projectId);
            }
        } else {
            project.status = ProjectStatus.Failed;
            // 如果开启了阶段点，按比例退还已发放部分
            if (project.hasStages) {
                _calculateProportionalRefund(projectId);
            }
        }

        emit ProjectFinished(projectId, project.status, project.pledged, project.goal);
    }

    // 按比例计算阶段点释放金额
    function _calculateProportionalRelease(uint256 projectId) private {
        Stage[] storage stages = projectStages[projectId];
        Project storage project = projects[projectId];

        for (uint256 i = 0; i < stages.length; i++) {
            if (stages[i].released) continue;

            uint256 requiredPledged = (project.goal * stages[i].completionThresholdBps) / BPS;
            if (project.pledged >= requiredPledged) {
                // 标记为已完成
                stages[i].completed = true;
                // 按比例计算释放金额
                uint256 releaseAmount = (project.pledged * stages[i].releaseBps) / BPS;
                stages[i].released = true;
                emit StageReleased(projectId, i, releaseAmount);
            }
        }
    }

    // 按比例计算失败时的退款金额
    // 关键逻辑：即使发起者未确认阶段点完成，只要已达标，对应资金自动保留
    function _calculateProportionalRefund(uint256 projectId) private {
        Stage[] storage stages = projectStages[projectId];
        Project storage project = projects[projectId];

        // 计算所有已达标阶段点的应保留金额（基于目标金额，不是筹集金额）
        uint256 autoRetained = 0;
        
        for (uint256 i = 0; i < stages.length; i++) {
            uint256 requiredPledged = (project.goal * stages[i].completionThresholdBps) / BPS;
            if (project.pledged >= requiredPledged) {
                // 已达标，自动保留（基于目标金额）
                uint256 releaseAmount = (project.goal * stages[i].releaseBps) / BPS;
                autoRetained += releaseAmount;
                
                // 自动标记阶段点为已完成和已释放（无论发起者是否确认）
                if (!stages[i].completed) {
                    stages[i].completed = true;
                }
                if (!stages[i].released) {
                    stages[i].released = true;
                }
            }
        }

        // 更新 totalWithdrawn 为所有已达标阶段点的保留金额
        // 这些金额将保留给发起者，不可退还
        project.totalWithdrawn = autoRetained;
    }

    function creatorWithdraw(uint256 projectId) external projectExists(projectId) onlyCreator(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Successful || project.status == ProjectStatus.Failed, "project not successful or failed");
        require(!project.creatorWithdrawn, "already withdrawn");
        require(project.balance > 0, "nothing to withdraw");

        uint256 amount = project.balance;
        project.balance = 0;
        project.creatorWithdrawn = true;
        project.totalWithdrawn += amount;

        (bool success, ) = payable(project.creator).call{value: amount}("");
        require(success, "withdraw failed");

        emit CreatorWithdrawal(projectId, project.creator, amount);
    }

    function refund(uint256 projectId) external projectExists(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Failed, "project not failed");

        uint256 donationAmount = donations[projectId][msg.sender];
        require(donationAmount > 0, "nothing to refund");

        // 计算可退款比例
        // 已释放的阶段点资金基于目标金额
        // 剩余资金 = 筹集金额 - 已释放金额
        // 退款比例 = 剩余资金 / 筹集金额
        
        uint256 totalPledged = project.pledged;
        uint256 totalWithdrawn = project.totalWithdrawn; // 已释放的阶段点资金
        
        // 计算可退款比例（基点）
        uint256 refundBps = 0;
        if (totalPledged > totalWithdrawn) {
            refundBps = ((totalPledged - totalWithdrawn) * BPS) / totalPledged;
        }
        
        // 计算实际退款金额
        uint256 refundAmount = (donationAmount * refundBps) / BPS;
        require(refundAmount > 0, "nothing to refund after stage release");
        require(project.balance >= refundAmount, "insufficient project balance");

        donations[projectId][msg.sender] = 0;
        project.totalRefunded += refundAmount;
        project.balance -= refundAmount;

        (bool success, ) = payable(msg.sender).call{value: refundAmount}("");
        require(success, "refund failed");

        emit DonationRefunded(projectId, msg.sender, refundAmount);
    }

    function completeStage(uint256 projectId, uint256 stageIndex) external projectExists(projectId) onlyCreator(projectId) {
        Stage storage stage = projectStages[projectId][stageIndex];
        require(!stage.completed, "already completed");
        stage.completed = true;
        emit StageCompleted(projectId, stageIndex);
    }

    function releaseStageFunds(uint256 projectId, uint256 stageIndex) external projectExists(projectId) onlyCreator(projectId) {
        Project storage project = projects[projectId];
        require(project.status == ProjectStatus.Active || project.status == ProjectStatus.Successful || project.status == ProjectStatus.Failed, "project not active or successful");

        Stage storage stage = projectStages[projectId][stageIndex];
        require(stage.completed, "stage not completed");
        require(!stage.released, "already released");

        uint256 requiredPledged = (project.goal * stage.completionThresholdBps) / BPS;
        require(project.pledged >= requiredPledged, "threshold not reached");

        uint256 amount = (project.goal * stage.releaseBps) / BPS;
        require(amount > 0, "nothing to release");
        require(project.balance >= amount, "insufficient balance");

        stage.released = true;
        project.balance -= amount;
        project.totalWithdrawn += amount;

        (bool success, ) = payable(project.creator).call{value: amount}("");
        require(success, "stage release failed");

        emit StageReleased(projectId, stageIndex, amount);
    }

    function getProject(uint256 projectId)
        external
        view
        projectExists(projectId)
        returns (
            uint256 id,
            address creator,
            string memory name,
            string memory description,
            uint256 goal,
            uint256 deadline,
            uint256 pledged,
            uint256 balance,
            uint256 totalWithdrawn,
            uint256 totalRefunded,
            ProjectStatus status,
            bool ended,
            bool creatorWithdrawn,
            uint256 donorCount,
            bool hasStages,
            bool hasMonthlySupport,
            uint256 stageCount,
            uint256 rewardCount
        )
    {
        Project storage project = projects[projectId];
        return (
            project.id,
            project.creator,
            project.name,
            project.description,
            project.goal,
            project.deadline,
            project.pledged,
            project.balance,
            project.totalWithdrawn,
            project.totalRefunded,
            project.status,
            project.ended,
            project.creatorWithdrawn,
            project.donorCount,
            project.hasStages,
            project.hasMonthlySupport,
            projectStages[projectId].length,
            projectRewards[projectId].length
        );
    }

    function getProjectIds() external view returns (uint256[] memory) {
        return projectIds;
    }

    function getDonors(uint256 projectId) external view projectExists(projectId) returns (address[] memory) {
        return projectDonors[projectId];
    }

    function getDonation(uint256 projectId, address donor) external view projectExists(projectId) returns (uint256) {
        return donations[projectId][donor];
    }

    function isEarlySupporter(uint256 projectId, address donor) external view projectExists(projectId) returns (bool) {
        return earlySupporters[projectId][donor];
    }

    function isMonthlySupporter(uint256 projectId, address donor) external view projectExists(projectId) returns (bool) {
        return monthlySupporters[projectId][donor];
    }

    function getStage(uint256 projectId, uint256 stageIndex)
        external
        view
        projectExists(projectId)
        returns (
            string memory description,
            uint256 completionThresholdBps,
            uint256 releaseBps,
            bool completed,
            bool released
        )
    {
        Stage storage stage = projectStages[projectId][stageIndex];
        return (
            stage.description,
            stage.completionThresholdBps,
            stage.releaseBps,
            stage.completed,
            stage.released
        );
    }

    function getStages(uint256 projectId) external view projectExists(projectId) returns (Stage[] memory) {
        return projectStages[projectId];
    }

    function getReward(uint256 projectId, uint256 rewardIndex)
        external
        view
        projectExists(projectId)
        returns (
            uint256 fundingThreshold,
            string memory promiseText,
            uint256 expectedMonth,
            uint256 backersCount
        )
    {
        Reward storage reward = projectRewards[projectId][rewardIndex];
        return (
            reward.fundingThreshold,
            reward.promiseText,
            reward.expectedMonth,
            reward.backersCount
        );
    }

    function getRewards(uint256 projectId) external view projectExists(projectId) returns (Reward[] memory) {
        return projectRewards[projectId];
    }

    function getMonthlySupport(uint256 projectId, address donor) external view projectExists(projectId) returns (uint256 monthlyAmount, uint256 nextBillingTime, bool active) {
        MonthlySupport storage support = monthlySupports[projectId][donor];
        return (support.monthlyAmount, support.nextBillingTime, support.active);
    }

    function getProjectDonorCount(uint256 projectId) external view projectExists(projectId) returns (uint256) {
        return projectDonors[projectId].length;
    }

    function getProjectDonor(uint256 projectId, uint256 index) external view projectExists(projectId) returns (address) {
        return projectDonors[projectId][index];
    }
}
