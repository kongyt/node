# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: element_msg.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='element_msg.proto',
  package='node',
  syntax='proto2',
  serialized_pb=_b('\n\x11\x65lement_msg.proto\x12\x04node\"\\\n\nElementMsg\x12\r\n\x05msgId\x18\x01 \x01(\x05\x12\x14\n\x0c\x66rom_element\x18\x02 \x01(\t\x12\x12\n\nto_element\x18\x03 \x01(\t\x12\x15\n\rserializeData\x18\x04 \x01(\t\"\x13\n\x04Helo\x12\x0b\n\x03txt\x18\x01 \x01(\t*\x15\n\x06\x45leMsg\x12\x0b\n\x07\x45M_HELO\x10\x01\x42\x1a\n\x18\x63om.kongyt.node.messages')
)

_ELEMSG = _descriptor.EnumDescriptor(
  name='EleMsg',
  full_name='node.EleMsg',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='EM_HELO', index=0, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=142,
  serialized_end=163,
)
_sym_db.RegisterEnumDescriptor(_ELEMSG)

EleMsg = enum_type_wrapper.EnumTypeWrapper(_ELEMSG)
EM_HELO = 1



_ELEMENTMSG = _descriptor.Descriptor(
  name='ElementMsg',
  full_name='node.ElementMsg',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='msgId', full_name='node.ElementMsg.msgId', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='from_element', full_name='node.ElementMsg.from_element', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='to_element', full_name='node.ElementMsg.to_element', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='serializeData', full_name='node.ElementMsg.serializeData', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=27,
  serialized_end=119,
)


_HELO = _descriptor.Descriptor(
  name='Helo',
  full_name='node.Helo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='txt', full_name='node.Helo.txt', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto2',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=121,
  serialized_end=140,
)

DESCRIPTOR.message_types_by_name['ElementMsg'] = _ELEMENTMSG
DESCRIPTOR.message_types_by_name['Helo'] = _HELO
DESCRIPTOR.enum_types_by_name['EleMsg'] = _ELEMSG
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ElementMsg = _reflection.GeneratedProtocolMessageType('ElementMsg', (_message.Message,), dict(
  DESCRIPTOR = _ELEMENTMSG,
  __module__ = 'element_msg_pb2'
  # @@protoc_insertion_point(class_scope:node.ElementMsg)
  ))
_sym_db.RegisterMessage(ElementMsg)

Helo = _reflection.GeneratedProtocolMessageType('Helo', (_message.Message,), dict(
  DESCRIPTOR = _HELO,
  __module__ = 'element_msg_pb2'
  # @@protoc_insertion_point(class_scope:node.Helo)
  ))
_sym_db.RegisterMessage(Helo)


DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), _b('\n\030com.kongyt.node.messages'))
# @@protoc_insertion_point(module_scope)