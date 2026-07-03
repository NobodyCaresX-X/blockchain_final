require("dotenv").config();
require("@nomicfoundation/hardhat-toolbox");

const localhostUrl = process.env.LOCALHOST_RPC_URL || "http://127.0.0.1:8545";

module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true
    },
  },
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {
      accounts: {
        count: 20,
        accountsBalance: "10000"
      },
      mining: {
        auto: true,
        interval: 0
      },
      hardfork: "london"
    },
    localhost: {
      url: localhostUrl
    },
  },
  hardhat: {
    networkConfig: {
      gasPrice: 0,
      baseFeePerGas: 0
    }
  }
};
