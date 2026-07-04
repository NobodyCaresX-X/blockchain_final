const state = {
  bootstrap: null,
  projects: [],
  currentAccount: null,
  milestoneCount: 0,
  currentUser: null,
  users: {},
  metamaskConnected: false,
  metamaskAddress: null,
  web3: null,
  contract: null,
  contractAddress: null,
};

function isMetamaskAvailable() {
  return typeof window !== "undefined" && window.ethereum && window.ethereum.isMetaMask;
}

async function initWeb3() {
  try {
    const contractInfo = await apiContractInfo();
    if (!contractInfo.ready || !contractInfo.address) {
      console.log("合约未就绪");
      return false;
    }

    state.contractAddress = contractInfo.address;

    if (isMetamaskAvailable()) {
      try {
        const accounts = await window.ethereum.request({ method: "eth_accounts" });
        if (accounts.length > 0) {
          state.web3 = new Web3(window.ethereum);
          state.metamaskAddress = accounts[0];
          state.metamaskConnected = true;
          updateMetamaskStatus();
        } else {
          state.web3 = new Web3(contractInfo.networkConfig.rpcUrls[0]);
        }
      } catch (error) {
        console.warn("Metamask不可用，使用RPC连接:", error.message);
        state.web3 = new Web3(contractInfo.networkConfig.rpcUrls[0]);
      }
    } else {
      state.web3 = new Web3(contractInfo.networkConfig.rpcUrls[0]);
    }

    state.contract = new state.web3.eth.Contract(contractInfo.abi, state.contractAddress);

    console.log("众筹合约已加载到前端");
    console.log("合约地址:", state.contractAddress);

    return true;
  } catch (error) {
    console.error("初始化Web3失败:", error);
    return false;
  }
}

async function connectMetamask() {
  if (!isMetamaskAvailable()) {
    alert("请安装Metamask浏览器插件！");
    return false;
  }
  
  try {
    const contractInfo = await apiContractInfo();
    const targetChainId = contractInfo.networkConfig.chainId;
    
    const currentChainId = await window.ethereum.request({ method: "eth_chainId" });
    if (currentChainId !== targetChainId) {
      try {
        await window.ethereum.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: targetChainId }],
        });
      } catch (switchError) {
        if (switchError.code === 4902) {
          await window.ethereum.request({
            method: "wallet_addEthereumChain",
            params: [{
              chainId: targetChainId,
              chainName: contractInfo.networkConfig.chainName,
              nativeCurrency: contractInfo.networkConfig.nativeCurrency,
              rpcUrls: contractInfo.networkConfig.rpcUrls,
              blockExplorerUrls: contractInfo.networkConfig.blockExplorerUrls,
            }],
          });
        } else {
          throw switchError;
        }
      }
    }

    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    if (accounts.length > 0) {
      state.metamaskAddress = accounts[0];
      state.metamaskConnected = true;
      updateMetamaskStatus();
      
      if (!state.web3) {
        state.web3 = new Web3(window.ethereum);
        state.contractAddress = contractInfo.address;
        state.contract = new state.web3.eth.Contract(contractInfo.abi, state.contractAddress);
      }
      
      return true;
    }
  } catch (error) {
    console.error("连接Metamask失败:", error);
    alert("连接Metamask失败，请确保已安装并解锁钱包，且同意切换到Hardhat网络");
  }
  return false;
}

function updateMetamaskStatus() {
  const metamaskBtn = document.getElementById("metamaskBtn");
  if (metamaskBtn) {
    if (state.metamaskConnected && state.metamaskAddress) {
      metamaskBtn.textContent = `🟢 ${formatAddress(state.metamaskAddress)}`;
      metamaskBtn.classList.add("connected");
    } else {
      metamaskBtn.textContent = "🔌 连接Metamask";
      metamaskBtn.classList.remove("connected");
    }
  }
}

async function signMessage(message) {
  if (!state.metamaskAddress || !window.ethereum) {
    throw new Error("请先连接Metamask");
  }

  // personal_sign 接受字符串消息，不需要转换为十六进制
  const signature = await window.ethereum.request({
    method: "personal_sign",
    params: [message, state.metamaskAddress],
  });
  return signature;
}

function formatEth(valueEth) {
  return Number(valueEth).toFixed(4);
}

function formatDeadline(secondsLeft) {
  if (secondsLeft <= 0) return "已结束";
  const hours = Math.floor(secondsLeft / 3600);
  const minutes = Math.floor((secondsLeft % 3600) / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}天 ${hours % 24}小时`;
  return `${hours}h ${minutes}m`;
}

function statusBadge(status) {
  const map = {
    Active: "进行中",
    Successful: "已完成",
    Failed: "已失效",
  };
  return map[status] || status;
}

function formatAddress(address) {
  if (!address) return "-";
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function getAddressDisplay(address) {
  const user = state.users[address.toLowerCase()] || state.users[address];
  if (user) {
    return `<span class="account-nickname">${user.nickname}</span><span class="account-address">${formatAddress(address)}</span>`;
  }
  return formatAddress(address);
}

function getAddressLabel(address) {
  const user = state.users[address.toLowerCase()] || state.users[address];
  if (user) {
    return `${user.nickname} (${formatAddress(address)})`;
  }
  return formatAddress(address);
}

async function apiBootstrap() {
  const response = await fetch("/api/bootstrap");
  return await response.json();
}

async function apiProjects() {
  const response = await fetch("/api/projects");
  return await response.json();
}

async function apiCheckAndFinishExpired() {
  try {
    const result = await state.contract.methods.checkAndFinishExpired().send({
      from: state.currentAccount || state.bootstrap.accounts[0],
      gas: 2000000
    });
    return result;
  } catch (error) {
    console.log("Check and finish expired failed:", error.message);
    return null;
  }
}

async function refreshProjects() {
  const projects = await apiProjects();
  state.projects = projects;
  if (typeof renderProjectsList === 'function') renderProjectsList();
}

async function checkExpiredProjects() {
  await apiCheckAndFinishExpired();
  
  const projects = await apiProjects();
  for (const project of projects) {
    if (project.status === "Active" && project.timeLeftSeconds <= 0) {
      console.log(`Project ${project.id} still active after auto-finish check`);
    }
  }
  state.projects = projects;
  if (typeof renderProjectsList === 'function') renderProjectsList();
}

async function apiProject(projectId) {
  const response = await fetch(`/api/projects/${projectId}`);
  return await response.json();
}

async function apiCreate(payload) {
  const response = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "创建失败");
  }
  return await response.json();
}

async function apiDonate(projectId, payload) {
  const token = localStorage.getItem("authToken");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`/api/projects/${projectId}/donate`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "捐赠失败");
  }
  return await response.json();
}

async function apiContractInfo() {
  try {
    const response = await fetch("/api/contract/info");
    if (!response.ok) {
      console.error(`合约信息API错误: ${response.status}`);
      return { ready: false, address: null, abi: [], networkConfig: {} };
    }
    return await response.json();
  } catch (error) {
    console.error("获取合约信息失败:", error);
    return { ready: false, address: null, abi: [], networkConfig: {} };
  }
}

async function addNetworkToMetamask(auto = false) {
  if (!isMetamaskAvailable()) {
    if (!auto) {
      alert("请安装Metamask浏览器插件！");
    }
    return false;
  }

  try {
    const contractInfo = await apiContractInfo();
    if (!contractInfo.ready) {
      if (!auto) {
        alert("合约未就绪，请稍后再试");
      }
      return false;
    }

    const networkConfig = contractInfo.networkConfig;
    
    try {
      // 尝试切换到网络
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: networkConfig.chainId }],
      });
      return true;
    } catch (switchError) {
      // 如果网络不存在，添加网络
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [networkConfig],
          });
          return true;
        } catch (addError) {
          console.error('添加网络失败:', addError);
          if (!auto) {
            alert('添加网络失败: ' + addError.message);
          }
          return false;
        }
      } else {
        console.error('切换网络失败:', switchError);
        if (!auto) {
          alert('切换网络失败: ' + switchError.message);
        }
        return false;
      }
    }
  } catch (error) {
    console.error('添加网络失败:', error);
    if (!auto) {
      alert('添加网络失败: ' + error.message);
    }
    return false;
  }
}

async function addContractToMetamask(auto = false) {
  if (!isMetamaskAvailable()) {
    if (!auto) {
      alert("请安装Metamask浏览器插件！");
    }
    return false;
  }

  try {
    const contractInfo = await apiContractInfo();
    if (!contractInfo.ready || !contractInfo.address) {
      if (!auto) {
        alert("合约未就绪，请稍后再试");
      }
      return false;
    }

    // 先添加网络
    const networkAdded = await addNetworkToMetamask(auto);
    if (!networkAdded) {
      return false;
    }

    // 自动模式下直接添加合约，手动模式下显示信息
    if (auto) {
      // 使用wallet_watchAsset添加合约
      try {
        await window.ethereum.request({
          method: 'wallet_watchAsset',
          params: {
            type: 'ERC20',
            options: {
              address: contractInfo.address,
              symbol: 'CROWD',
              decimals: 0,
            },
          },
        });
        console.log("众筹合约已自动添加到Metamask");
        return true;
      } catch (error) {
        // 如果用户拒绝或其他错误，不显示提示
        console.log('自动添加合约被跳过:', error.message);
        return false;
      }
    } else {
      // 手动模式：显示合约信息
      const message = `
众筹合约信息已准备好！

合约地址: ${contractInfo.address}

请在Metamask中手动导入合约：
1. 点击"导入代币"或"导入合约"
2. 选择"自定义代币"
3. 粘贴合约地址: ${contractInfo.address}
4. 代币符号: CROWD
5. 小数位数: 0

注意：众筹合约不是ERC20代币，主要用于在Metamask中查看合约交互历史。
      `;
      
      alert(message);
      
      navigator.clipboard.writeText(contractInfo.address).then(() => {
        console.log('合约地址已复制到剪贴板');
      }).catch(err => {
        console.error('复制失败:', err);
      });
      
      return true;
    }
  } catch (error) {
    console.error('添加合约失败:', error);
    if (!auto) {
      alert('添加合约失败: ' + error.message);
    }
    return false;
  }
}

async function apiFinish(projectId, from) {
  const token = localStorage.getItem("authToken");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`/api/projects/${projectId}/finish`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ from }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "结束失败");
  }
  return await response.json();
}

async function apiWithdraw(projectId, from) {
  const response = await fetch(`/api/projects/${projectId}/withdraw`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "提现失败");
  }
  return await response.json();
}

async function apiCompleteMilestone(projectId, index, from) {
  const token = localStorage.getItem("authToken");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`/api/projects/${projectId}/milestones/${index}/complete`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ from }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "完成里程碑失败");
  }
  return await response.json();
}

async function apiReleaseMilestone(projectId, index, from) {
  const token = localStorage.getItem("authToken");
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`/api/projects/${projectId}/milestones/${index}/release`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({ from }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "释放里程碑资金失败");
  }
  return await response.json();
}

async function apiRefund(projectId, from) {
  const response = await fetch(`/api/projects/${projectId}/refund`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "退款失败");
  }
  return await response.json();
}

async function apiGetTransactions() {
  const response = await fetch("/api/user/transactions");
  if (!response.ok) {
    return [];
  }
  return await response.json();
}

async function apiCompleteMilestone(projectId, index, from) {
  const response = await fetch(`/api/projects/${projectId}/milestones/${index}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "标记失败");
  }
  return await response.json();
}

async function apiGetUsers() {
  const response = await fetch("/api/users");
  return await response.json();
}

async function apiGetBalance(address) {
  const response = await fetch(`/api/user/balance/${address}`);
  return await response.json();
}

async function apiUserMe() {
  const token = localStorage.getItem("authToken");
  if (!token) return { authenticated: false };
  
  const response = await fetch("/api/user/me", {
    headers: { "Authorization": `Bearer ${token}` }
  });
  return await response.json();
}

async function initCommon() {
  try {
    state.bootstrap = await apiBootstrap();
    state.projects = state.bootstrap.projects || [];
    
    const users = await apiGetUsers();
    users.forEach(u => {
      state.users[u.address.toLowerCase()] = u;
    });
    
    await refreshCurrentUser();
    
    updateNavStatus();
    updateUserInfo();
    
    return true;
  } catch (error) {
    console.error("初始化失败:", error);
    const statusDot = document.getElementById("statusDot");
    if (statusDot) statusDot.classList.add("error");
    const statusText = document.getElementById("statusText");
    if (statusText) statusText.textContent = "连接失败";
    return false;
  }
}

async function refreshCurrentUser() {
  const userMe = await apiUserMe();
  if (userMe.authenticated) {
    state.currentUser = userMe.user;
    state.currentAccount = userMe.user.address;
  }
}

function updateNavStatus() {
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  
  if (state.bootstrap?.ready) {
    statusDot.className = "status-dot ready";
    statusText.textContent = "已连接";
  } else {
    statusDot.className = "status-dot error";
    statusText.textContent = "未连接";
  }
}

function updateUserInfo() {
  const userInfo = document.getElementById("userInfo");
  if (!userInfo) return;
  
  if (state.currentUser) {
    userInfo.innerHTML = `
      <div class="user-nickname">${state.currentUser.nickname}</div>
      <div class="user-balance">余额: ${formatEth(state.currentUser.external_balance)} ETH</div>
      <a href="/wallet" class="btn-secondary btn-sm">钱包</a>
      <button class="btn-logout" onclick="logout()">退出</button>
    `;
  } else {
    userInfo.innerHTML = `
      <a href="/login" class="btn-secondary btn-sm">登录</a>
      <a href="/register" class="btn-primary btn-sm">注册</a>
    `;
  }
}

function logout() {
  localStorage.removeItem("authToken");
  localStorage.removeItem("currentUser");
  state.currentUser = null;
  state.currentAccount = null;
  updateUserInfo();
  window.location.href = "/login";
}

function populateAccounts(selectId) {
  const select = document.getElementById(selectId);
  if (!select || !state.bootstrap?.accounts) return;
  
  const currentValue = select.value;
  select.innerHTML = state.bootstrap.accounts.map(account => {
    const label = getAddressLabel(account);
    return `<option value="${account}">${label}</option>`;
  }).join("");
  
  if (state.currentUser && !currentValue) {
    select.value = state.currentUser.address;
  } else if (currentValue && state.bootstrap.accounts.includes(currentValue)) {
    select.value = currentValue;
  }
}

function getDisplayPledged(project) {
  if (project.status === "Successful" && project.rewardCount === 0 && project.pledgedEth > project.goalEth) {
    return project.goalEth;
  }
  return project.pledgedEth;
}

function renderProjectCard(project, showActions = true) {
  // 处理捐赠者标签
  const donors = (project.donors || []).map(donor => {
    const tags = [];
    if (donor.earlySupporter) tags.push('<em class="reward-tag early">天使投资</em>');
    if (donor.monthlySupporter) tags.push('<em class="reward-tag monthly">月度会员</em>');
    
    let displayAmount = donor.donationEth;
    if (project.status === "Successful" && project.rewardCount === 0 && project.pledgedEth > project.goalEth) {
      const refundRatio = (project.pledgedEth - project.goalEth) / project.pledgedEth;
      displayAmount = donor.donationEth * (1 - refundRatio);
    }
    
    return `
    <li>
      <span>${getAddressDisplay(donor.address)}</span>
      <strong>${formatEth(displayAmount)} ETH</strong>
      ${tags.length > 0 ? tags.join(' ') : ''}
    </li>
  `}).join("");

  // 阶段点（分批释放资金）
  const stages = project.stages && project.stages.length > 0 ? project.stages.map(s => `
    <li>
      <span>#${s.index + 1} ${s.description || "阶段"}</span>
      <small>${s.completionThresholdBps / 100}% 触发，释放 ${s.releaseBps / 100}%</small>
      <strong>${s.completed ? "✓ 完成" : "○ 进行中"}${s.released ? " / 已释放" : ""}</strong>
    </li>
  `).join("") : "";

  // 里程碑/奖励（发起者承诺）
  const rewards = project.rewards && project.rewards.length > 0 ? project.rewards.map(r => `
    <li class="reward-item">
      <div><strong>#${r.index + 1} 里程碑</strong></div>
      <div>达标线: ${formatEth(r.fundingThresholdEth)} ETH</div>
      <div>承诺: ${r.promise || "暂无"}</div>
      <div><small>预计 ${r.expectedMonth} 个月内实现</small></div>
    </li>
  `).join("") : "";

  // 项目特性标签
  const featureTags = [];
  if (project.hasStages) featureTags.push('<span class="stages-tag">阶段点</span>');
  if (project.hasMonthlySupport) featureTags.push('<span class="monthly-tag">月度支持</span>');

  const isCreator = state.currentUser && project.creator.toLowerCase() === state.currentUser.address.toLowerCase();
  const isSupporter = state.currentUser && project.donors && project.donors.some(d => d.address.toLowerCase() === state.currentUser.address.toLowerCase());
  
  // 检查用户是否是月度支持者
  const isMonthlySupporter = state.currentUser && project.donors && project.donors.some(d => 
    d.address.toLowerCase() === state.currentUser.address.toLowerCase() && d.monthlySupporter
  );
  
  // 阶段点操作按钮（在进行中、已完成、已失效状态下都可操作）
  const canManageStages = isCreator && project.stages && project.stages.length > 0 && 
    (project.status === "Active" || project.status === "Successful" || project.status === "Failed");
  
  const stageActions = canManageStages ? project.stages.map((s, i) => {
    const threshold = (project.goalEth * s.completionThresholdBps) / 10000;
    const reached = parseFloat(project.pledgedEth) >= parseFloat(threshold);
    
    if (s.completed && !s.released) {
      return `<button class="btn-success btn-small" onclick="releaseMilestone(${project.id}, ${i})">释放阶段 #${i + 1} 资金</button>`;
    } else if (!s.completed && reached) {
      return `<button class="btn-primary btn-small" onclick="completeMilestone(${project.id}, ${i})">完成阶段 #${i + 1}</button>`;
    }
    return "";
  }).join("") : "";
  
  const actions = showActions ? `
    <div class="project-actions">
      ${project.status === "Active" && !isCreator && project.timeLeftSeconds > 0 ? `
        <button class="btn-primary btn-small" onclick="openDonateModal(${project.id})">💝 支持</button>
        ${project.hasMonthlySupport ? `<button class="btn-secondary btn-small" onclick="openMonthlySupportModal(${project.id})">🌊 长期支持</button>` : ''}
      ` : ""}
      ${(project.status === "Successful" || project.status === "Failed") && !project.creatorWithdrawn && project.balanceEth > 0 && isCreator ? `<button class="btn-success btn-small" onclick="withdrawFunds(${project.id})">提取资金</button>` : ""}
      ${project.status === "Failed" ? `<button class="btn-secondary btn-small" onclick="getRefund(${project.id})">退款</button>` : ""}
      ${stageActions}
    </div>
  ` : "";

  return `
    <article class="project-card">
      <header>
        <div>
          <p class="project-id">项目 #${project.id}</p>
          <h4>${project.name}</h4>
          ${featureTags.length > 0 ? `<div class="feature-tags">${featureTags.join('')}</div>` : ''}
        </div>
        <span class="status ${project.status.toLowerCase()}">${statusBadge(project.status)}</span>
      </header>
      <p class="project-desc">${project.description}</p>
      <div class="stats">
        <div><span>目标</span><strong>${formatEth(project.goalEth)} ETH</strong></div>
        <div><span>已筹</span><strong>${formatEth(getDisplayPledged(project))} ETH</strong></div>
        <div><span>剩余</span><strong>${formatDeadline(project.timeLeftSeconds)}</strong></div>
        <div><span>进度</span><strong>${project.goalEth > 0 ? Math.min(100, Math.round(getDisplayPledged(project) / project.goalEth * 100)) : 0}%</strong></div>
      </div>
      ${actions}
      <div class="project-details">
        <details>
          <summary>查看详情</summary>
          <div class="detail-content">
            <div class="detail-grid">
              <div><span>发起人</span><code>${getAddressDisplay(project.creator)}</code></div>
              <div><span>截止时间</span><code>${new Date(project.deadlineIso).toLocaleString()}</code></div>
              <div><span>捐赠者</span><code>${project.donorCount} 人</code></div>
              <div><span>阶段点</span><code>${project.stageCount} 个</code></div>
              <div><span>里程碑</span><code>${project.rewardCount} 个</code></div>
            </div>
            ${stages ? `<div class="list-block"><h5>阶段点（分批释放）</h5><ul class="compact-list">${stages}</ul></div>` : ""}
            ${rewards ? `<div class="list-block"><h5>里程碑（发起者承诺）</h5><ul class="compact-list">${rewards}</ul></div>` : ""}
            ${donors ? `<div class="list-block"><h5>支持者</h5><ul class="compact-list">${donors}</ul></div>` : ""}
          </div>
        </details>
      </div>
    </article>
  `;
}

async function initHomePage() {
  const ready = await initCommon();
  if (!ready) return;

  const rpcUrlEl = document.getElementById("rpcUrl");
  if (rpcUrlEl) rpcUrlEl.textContent = state.bootstrap.rpcUrl?.includes("tester") ? "Python 测试链" : "外部链";
  
  const contractAddressEl = document.getElementById("contractAddress");
  if (contractAddressEl) contractAddressEl.textContent = formatAddress(state.bootstrap.contractAddress);
  
  const accountCountEl = document.getElementById("accountCount");
  if (accountCountEl) accountCountEl.textContent = `${state.bootstrap.accounts?.length || 0} 个`;
  
  const projectCountEl = document.getElementById("projectCount");
  if (projectCountEl) projectCountEl.textContent = `${state.projects.length} 个`;
  
  const statusChipEl = document.getElementById("statusChip");
  if (statusChipEl) {
    statusChipEl.textContent = state.bootstrap.ready ? "就绪" : "等待";
    statusChipEl.className = state.bootstrap.ready ? "status-chip ready" : "status-chip waiting";
  }

  const container = document.getElementById("recentProjects");
  if (container) {
    const recentProjects = state.projects.slice(-3).reverse();
    if (recentProjects.length === 0) {
      container.innerHTML = `<div class="empty-state">暂无项目，<a href="/create">创建第一个项目</a></div>`;
    } else {
      container.innerHTML = recentProjects.map(p => renderProjectCard(p, false)).join("");
    }
  }
}

async function initProjectsPage() {
  const ready = await initCommon();
  if (!ready) return;

  state.projects = await apiProjects();
  renderProjectsList();

  document.getElementById("refreshBtn").addEventListener("click", async () => {
    state.projects = await apiProjects();
    renderProjectsList();
  });

  document.getElementById("statusFilter").addEventListener("change", renderProjectsList);

  document.getElementById("donateForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const projectId = parseInt(form.projectId.value);
    const amountEth = parseFloat(form.amountEth.value);
    
    if (!state.currentUser) {
      alert("请先登录！");
      window.location.href = "/login";
      return;
    }
    
    if (!state.contract) {
      alert("合约未加载，请刷新页面！");
      return;
    }
    
    if (!state.metamaskAddress) {
      alert("请先连接Metamask！");
      connectMetamask();
      return;
    }
    
    try {
      const amountWei = state.web3.utils.toWei(amountEth.toString(), 'ether');
      
      // 捐赠前检查链上时间是否已超过截止时间
      const project = state.projects.find(p => p.id === projectId);
      if (project) {
        const chainBlock = await state.web3.eth.getBlock('latest');
        const chainTimestamp = chainBlock.timestamp;
        const deadline = parseInt(project.deadline);
        
        console.log(`捐赠前检查 - 链上时间: ${chainTimestamp}, 截止时间: ${deadline}, 差值: ${deadline - chainTimestamp}秒`);
        
        if (chainTimestamp >= deadline) {
          alert(`项目已在链上过期！链上时间: ${new Date(chainTimestamp * 1000).toLocaleString()}, 截止时间: ${new Date(deadline * 1000).toLocaleString()}`);
          return;
        }
        
        // 检查项目状态是否仍然活跃
        const projectInfo = await state.contract.methods.getProject(projectId).call();
        if (projectInfo.status !== '0') { // 0 = Active
          alert(`项目状态已变更: ${projectInfo.status === '1' ? '已完成' : '已失败'}`);
          return;
        }
      }
      
      // 普通捐赠
      const result = await state.contract.methods.donate(projectId).send({
        from: state.metamaskAddress,
        value: amountWei,
        gas: 2000000
      });
      
      alert(`支持成功！交易哈希: ${result.transactionHash.slice(0, 10)}...`);
      
      closeDonateModal();
      state.projects = await apiProjects();
      renderProjectsList();
      await refreshCurrentUser();
      updateUserInfo();
    } catch (error) {
      alert(error.message);
    }
  });
  
  // 长期支持表单提交
  document.getElementById("monthlySupportForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const projectId = parseInt(form.projectId.value);
    const monthlyAmountEth = parseFloat(form.monthlyAmountEth.value);
    
    if (!state.metamaskAddress) {
      alert("请先连接Metamask！");
      return;
    }
    
    await startMonthlySupport(projectId, monthlyAmountEth);
  });
}

function renderProjectsList() {
  const container = document.getElementById("projectsContainer");
  if (!container) return;
  
  const filterSelect = document.getElementById("statusFilter");
  const filter = filterSelect ? filterSelect.value : "all";
  
  let filtered = state.projects;
  if (filter !== "all") {
    filtered = state.projects.filter(p => p.status === filter);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">暂无${filter === "all" ? "" : statusBadge(filter)}项目</div>`;
    return;
  }
  
  container.innerHTML = filtered.map(p => renderProjectCard(p)).join("");
}

async function initCreatePage() {
  const ready = await initCommon();
  if (!ready) return;

  if (!state.currentUser) {
    alert("请先登录！");
    window.location.href = "/login";
    return;
  }

  document.getElementById("createForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    
    if (!state.currentUser) {
      alert("请先登录！");
      window.location.href = "/login";
      return;
    }
    
    if (!state.contract) {
      alert("合约未加载，请刷新页面！");
      return;
    }
    
    if (!state.metamaskAddress) {
      alert("请先连接Metamask！");
      connectMetamask();
      return;
    }
    
    // 收集阶段点数据
    const hasStages = form.hasStages?.checked || false;
    const stages = [];
    if (hasStages) {
      for (let i = 0; i <= 100; i++) {
        const desc = form[`stage_desc_${i}`]?.value;
        const threshold = form[`stage_threshold_${i}`]?.value;
        const release = form[`stage_release_${i}`]?.value;
        
        if (!desc && !threshold && !release) break;
        
        if (desc && threshold && release) {
          stages.push({
            description: desc,
            thresholdBps: parseInt(threshold) * 100,
            releaseBps: parseInt(release) * 100
          });
        }
      }
    }
    
    // 收集里程碑/奖励数据
    const rewards = [];
    for (let i = 0; i <= 100; i++) {
      const threshold = form[`reward_threshold_${i}`]?.value;
      const promise = form[`reward_promise_${i}`]?.value;
      const month = form[`reward_month_${i}`]?.value;
      
      if (!threshold && !promise && !month) break;
      
      if (threshold && promise && month) {
        rewards.push({
          thresholdWei: state.web3.utils.toWei(threshold, 'ether'),
          thresholdEth: parseFloat(threshold),
          promise: promise,
          month: parseInt(month)
        });
      }
    }
    
    // 月度支持
    const hasMonthlySupport = form.hasMonthlySupport?.checked || false;
    
    try {
      const goalWei = state.web3.utils.toWei(form.goalEth.value.toString(), 'ether');
      
      // 查询当前网络的gas价格
      let gasPrice = "0";
      try {
        const currentGasPrice = await state.web3.eth.getGasPrice();
        gasPrice = "0"; // Hardhat本地强制使用0
        console.log("网络Gas价格:", currentGasPrice, "-> 使用0");
      } catch (e) {
        console.warn("获取gas价格失败，使用0:", e.message);
      }
      
      // 调用合约创建项目
      // 使用链上时间计算截止时间，确保与合约时间一致
      const chainBlock = await state.web3.eth.getBlock('latest');
      const chainTimestamp = chainBlock.timestamp;
      
      // datetime-local 的值格式为 "YYYY-MM-DDTHH:mm"，需要加上秒数 ":00" 确保正确解析为本地时间
      const deadlineValue = form.deadline.value + ":00";
      const deadlineDate = new Date(deadlineValue);
      const deadlineTimestamp = Math.floor(deadlineDate.getTime() / 1000);
      
      // 计算用户期望的剩余时间（秒）
      const systemTimestamp = Math.floor(Date.now() / 1000);
      const expectedSeconds = deadlineTimestamp - systemTimestamp;
      
      console.log("=== 时间同步调试 ===");
      console.log("链上当前时间戳:", chainTimestamp);
      console.log("系统当前时间戳:", systemTimestamp);
      console.log("用户选择的截止时间戳:", deadlineTimestamp);
      console.log("用户期望的剩余时间:", Math.floor(expectedSeconds / 60), "分钟");
      
      // 使用链上时间 + 用户期望的剩余时间 = 实际截止时间
      let actualDeadline = chainTimestamp + expectedSeconds;
      
      // 确保截止时间至少比链上时间晚1分钟（最小有效时间）
      if (actualDeadline <= chainTimestamp) {
        actualDeadline = chainTimestamp + 60;
      }
      
      console.log(`最终截止时间: ${actualDeadline} (链上时间+${Math.floor(actualDeadline - chainTimestamp)}秒)`);
      
      const finalDiff = actualDeadline - chainTimestamp;
      console.log(`最终截止时间与链上时间差: ${finalDiff}秒 (${Math.floor(finalDiff/60)}分钟)`);
      
      const result = await state.contract.methods.createProject(
        form.name.value,
        form.description.value,
        goalWei,
        actualDeadline,
        hasStages,
        stages.map(s => s.description),
        stages.map(s => s.thresholdBps),
        stages.map(s => s.releaseBps),
        hasMonthlySupport,
        rewards.map(r => r.thresholdWei),
        rewards.map(r => r.promise),
        rewards.map(r => r.month)
      ).send({
        from: state.metamaskAddress,
        gas: 15000000
      });
      
      alert(`项目创建成功！交易哈希: ${result.transactionHash.slice(0, 10)}...`);
      window.location.href = "/projects";
    } catch (error) {
      alert(error.message);
    }
  });
}

async function initMyPage() {
  const ready = await initCommon();
  if (!ready) return;

  if (!state.currentUser) {
    alert("请先登录！");
    window.location.href = "/login";
    return;
  }

  updateMyPage();
}

async function updateMyPage() {
  if (!state.currentUser) return;

  const account = state.currentUser.address;

  const myProjectsContainer = document.getElementById("myProjects");
  const myProjects = state.projects.filter(p => p.creator.toLowerCase() === account.toLowerCase());
  if (myProjectsContainer) {
    myProjectsContainer.innerHTML = myProjects.length > 0 
      ? myProjects.map(p => renderProjectCard(p)).join("")
      : '<div class="empty-state">您还没有创建项目</div>';
  }

  const myDonations = [];
  state.projects.forEach(p => {
    p.donors.forEach(d => {
      if (d.address.toLowerCase() === account.toLowerCase()) {
        myDonations.push({ project: p, donation: d });
      }
    });
  });
  
  const myDonationsContainer = document.getElementById("myDonations");
  if (myDonationsContainer) {
    myDonationsContainer.innerHTML = myDonations.length > 0
      ? myDonations.map(({project, donation}) => `
        <div class="donation-item">
          <div class="donation-project">
            <strong>${project.name}</strong>
            <span class="status ${project.status.toLowerCase()}">${statusBadge(project.status)}</span>
          </div>
          <div class="donation-info">
            <span>捐赠金额: <strong>${formatEth(donation.donationEth)} ETH</strong></span>
            ${donation.earlySupporter ? '<em class="reward-tag">早期支持者</em>' : ''}
          </div>
        </div>
      `).join("")
      : '<div class="empty-state">您还没有捐赠记录</div>';
  }

  const refundProjects = state.projects.filter(p => 
    p.status === "Failed" && 
    p.donors.some(d => d.address.toLowerCase() === account.toLowerCase())
  );
  const refundProjectsContainer = document.getElementById("refundProjects");
  if (refundProjectsContainer) {
    refundProjectsContainer.innerHTML = refundProjects.length > 0
      ? refundProjects.map(p => renderProjectCard(p)).join("")
      : '<div class="empty-state">无待退款项目</div>';
  }
  
  await loadMyTransactions();
}

async function loadMyTransactions() {
  const container = document.getElementById("myTransactions");
  if (!container) return;
  
  try {
    const transactions = await apiGetTransactions();
    
    if (transactions.length === 0) {
      container.innerHTML = '<div class="empty-state">暂无交易记录</div>';
      return;
    }
    
    container.innerHTML = transactions.map(tx => {
      const typeColor = {
        donation: "#22c55e",
        refund: "#3b82f6",
        withdrawal: "#f59e0b",
        stage_release: "#8b5cf6",
      }[tx.type] || "#6b7280";
      
      const icon = {
        donation: "💝",
        refund: "↩️",
        withdrawal: "💰",
        stage_release: "📦",
      }[tx.type] || "📜";
      
      const project = state.projects.find(p => p.id === tx.projectId);
      
      return `
        <div class="transaction-item">
          <div class="transaction-icon" style="background: ${typeColor}20; color: ${typeColor}">
            ${icon}
          </div>
          <div class="transaction-info">
            <div class="transaction-header">
              <span class="transaction-type" style="color: ${typeColor}">${tx.typeLabel}</span>
              <span class="transaction-amount ${tx.type === 'donation' ? 'text-red' : 'text-green'}">
                ${tx.type === 'donation' ? '-' : '+'}${formatEth(tx.amount)} ETH
              </span>
            </div>
            <div class="transaction-project">
              ${project ? `<strong>${project.name}</strong>` : `项目 #${tx.projectId}`}
            </div>
            <div class="transaction-meta">
              <span class="transaction-hash">${tx.hash.slice(0, 10)}...</span>
              <span class="transaction-time">${new Date(tx.timestamp).toLocaleString()}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch (error) {
    console.error("加载交易记录失败:", error);
    container.innerHTML = '<div class="empty-state">加载交易记录失败</div>';
  }
}

function openDonateModal(projectId) {
  document.getElementById("donateProjectId").value = projectId;
  document.getElementById("donateModal").style.display = "flex";
}

function closeDonateModal() {
  document.getElementById("donateModal").style.display = "none";
}

// 月度支持相关函数
function openMonthlySupportModal(projectId) {
  document.getElementById("monthlySupportProjectId").value = projectId;
  const project = state.projects.find(p => p.id === projectId);
  if (project) {
    document.getElementById("monthlySupportInfo").innerHTML = `
      <p>项目: <strong>${project.name}</strong></p>
      <p>目标: ${formatEth(project.goalEth)} ETH</p>
      <p>已筹: ${formatEth(project.pledgedEth)} ETH (${project.goalEth > 0 ? Math.round(project.pledgedEth / project.goalEth * 100) : 0}%)</p>
    `;
  }
  document.getElementById("monthlySupportModal").style.display = "flex";
}

function closeMonthlySupportModal() {
  document.getElementById("monthlySupportModal").style.display = "none";
}

async function startMonthlySupport(projectId, monthlyAmountEth) {
  if (!confirm(`确定要开启长期支持，每月支持 ${monthlyAmountEth} ETH 吗？首次扣款将立即执行。`)) return;
  
  try {
    const result = await state.contract.methods.startMonthlySupport(projectId, state.web3.utils.toWei(monthlyAmountEth.toString(), 'ether')).send({
      from: state.metamaskAddress,
      value: state.web3.utils.toWei(monthlyAmountEth.toString(), 'ether'),
      gas: 15000000
    });
    
    alert(`长期支持已开启！交易哈希: ${result.transactionHash.slice(0, 10)}...`);
    closeMonthlySupportModal();
    state.projects = await apiProjects();
    if (typeof renderProjectsList === 'function') renderProjectsList();
    if (typeof updateMyPage === 'function') updateMyPage();
  } catch (error) {
    alert(error.message);
  }
}

async function stopMonthlySupport(projectId) {
  if (!confirm("确定要停止长期支持吗？")) return;
  
  const pid = projectId || document.getElementById("monthlySupportProjectId").value;
  
  try {
    const result = await state.contract.methods.stopMonthlySupport(parseInt(pid)).send({
      from: state.metamaskAddress,
      gas: 2000000
    });
    
    alert("长期支持已停止！");
    closeMonthlySupportModal();
    state.projects = await apiProjects();
    if (typeof renderProjectsList === 'function') renderProjectsList();
    if (typeof updateMyPage === 'function') updateMyPage();
  } catch (error) {
    alert(error.message);
  }
}

async function finishProject(projectId) {
  if (!confirm("确定要结束此项目吗？")) return;
  try {
    await apiFinish(projectId, state.currentUser.address);
    state.projects = await apiProjects();
    if (typeof renderProjectsList === 'function') renderProjectsList();
    if (typeof updateMyPage === 'function') updateMyPage();
    alert("项目已结束！");
  } catch (error) {
    alert(error.message);
  }
}

async function withdrawFunds(projectId) {
  if (!confirm("确定要提取资金吗？")) return;
  try {
    // 确保有有效的发送者地址
    const from = state.currentAccount || (state.bootstrap && state.bootstrap.accounts && state.bootstrap.accounts[0]);
    if (!from) {
      alert("请先登录或刷新页面！");
      return;
    }
    await apiWithdraw(projectId, from);
    state.projects = await apiProjects();
    if (typeof renderProjectsList === 'function') renderProjectsList();
    if (typeof updateMyPage === 'function') updateMyPage();
    alert("资金提取成功！");
  } catch (error) {
    alert(error.message);
  }
}

async function completeMilestone(projectId, index) {
  if (!confirm(`确定要标记阶段点 #${index + 1} 为完成吗？`)) return;
  try {
    const from = state.currentAccount || (state.bootstrap && state.bootstrap.accounts && state.bootstrap.accounts[0]);
    if (!from) {
      alert("请先登录或刷新页面！");
      return;
    }
    console.log("开始标记阶段点完成...", { projectId, index, from });
    const result = await apiCompleteMilestone(projectId, index, from);
    console.log("标记阶段点完成成功:", result);
    state.projects = await apiProjects();
    if (typeof renderProjectsList === 'function') renderProjectsList();
    if (typeof updateMyPage === 'function') updateMyPage();
    alert(`阶段点 #${index + 1} 已标记完成！`);
  } catch (error) {
    console.error("标记阶段点完成失败:", error);
    alert("操作失败: " + error.message);
  }
}

async function releaseMilestone(projectId, index) {
  if (!confirm(`确定要释放阶段点 #${index + 1} 的资金吗？`)) return;
  try {
    const from = state.currentAccount || (state.bootstrap && state.bootstrap.accounts && state.bootstrap.accounts[0]);
    if (!from) {
      alert("请先登录或刷新页面！");
      return;
    }
    console.log("开始释放阶段点资金...", { projectId, index, from });
    const result = await apiReleaseMilestone(projectId, index, from);
    console.log("释放阶段点资金成功:", result);
    state.projects = await apiProjects();
    if (typeof renderProjectsList === 'function') renderProjectsList();
    if (typeof updateMyPage === 'function') updateMyPage();
    alert(`阶段点 #${index + 1} 资金已释放！`);
  } catch (error) {
    console.error("释放阶段点资金失败:", error);
    alert("释放失败: " + error.message);
  }
}

async function getRefund(projectId) {
  if (!confirm("确定要申请退款吗？")) return;
  try {
    const from = state.currentAccount || (state.bootstrap && state.bootstrap.accounts && state.bootstrap.accounts[0]);
    if (!from) {
      alert("请先登录或刷新页面！");
      return;
    }
    
    const project = state.projects.find(p => p.id === projectId);
    const donor = project?.donors?.find(d => d.address.toLowerCase() === from.toLowerCase());
    const originalDonation = donor ? donor.donationEth : 0;
    
    const result = await apiRefund(projectId, from);
    state.projects = await apiProjects();
    await refreshCurrentUser();
    updateUserInfo();
    
    const newProject = state.projects.find(p => p.id === projectId);
    const newDonor = newProject?.donors?.find(d => d.address.toLowerCase() === from.toLowerCase());
    const refundedAmount = originalDonation - (newDonor ? newDonor.donationEth : 0);
    
    alert(`退款成功！\n交易哈希: ${result.txHash}\n退款金额: ${refundedAmount} ETH`);
  } catch (error) {
    let msg = error.message;
    if (msg.includes("nothing to refund")) msg = "您已经退过款了！";
    if (msg.includes("project not failed")) msg = "项目未失效，无法退款！";
    alert(msg);
  }
}

function closeActionModal() {
  document.getElementById("actionModal").style.display = "none";
}

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal")) {
    e.target.style.display = "none";
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(link => {
    if (link.getAttribute("href") === path) {
      link.classList.add("active");
    }
  });

  // 自动初始化Web3和众筹合约
  initWeb3();
});
