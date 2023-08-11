const WEBUI_ENDPOINT: string = "banana";

const STATIC_SUSBCRIBER_DATA = {
  plmnID: "20893",
};

const STATIC_DEVICE_GROUP_DATA = {
  "site-info": "default",
  "ip-domain-name": "pool1",
  "ip-domain-expanded": {
    dnn: "internet",
    "ue-ip-pool": "172.250.1.0/16",
    "dns-primary": "8.8.8.8",
    mtu: 1460,
    "ue-dnn-qos": {
      "dnn-mbr-uplink": 20000000,
      "dnn-mbr-downlink": 200000000,
      "traffic-class": {
        name: "platinum",
        arp: 6,
        pdb: 300,
        pelr: 6,
        qci: 8,
      },
    },
  },
};

const NETWORK_SLICE_NAME = "default";

const STATIC_NETWORK_SLICE_DATA = {
  "slice-id": {
    sst: 1,
    sd: "010203",
  },
  "site-device-group": ["default"],
  "site-info": {
    "site-name": "default",
    gNodeBs: [
      {
        name: "gnb1",
        tac: "1",
      },
    ],
    upf: {
      "upf-name": "pizza",
      "upf-port": "1234",
    },
  },
}

export {
  WEBUI_ENDPOINT,
  STATIC_SUSBCRIBER_DATA,
  STATIC_DEVICE_GROUP_DATA,
  STATIC_NETWORK_SLICE_DATA,
  NETWORK_SLICE_NAME,
};
