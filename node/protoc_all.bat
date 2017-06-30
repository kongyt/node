cd msg_define
protoc -I=./ --python_out=../pb mn_msg.proto
protoc -I=./ --python_out=../pb nn_msg.proto
protoc -I=./ --python_out=../pb cn_msg.proto
protoc -I=./ --python_out=../pb element_msg.proto