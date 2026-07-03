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
      viaIR: true,
    },
  },
  paths: {
    sources: "./contracts",
    artifacts: "./artifacts"
  },
  allowUnlimitedContractSize: true,
  defaultNetwork: "hardhat",
  networks: {
    hardhat: {},
    localhost: {
      url: "http://127.0.0.1:8545",
      accounts: { mnemonic: "test test test test test test test test test test test junk" }
    },
  },
};
