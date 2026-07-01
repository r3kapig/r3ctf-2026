from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel

class RegisterRequest(BaseModel):
    phone: str
    password: str
    handle: Optional[str] = None
    display_name: Optional[str] = None
    is_victim: bool = False

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    token: str
    user_id: str

class UserProfile(BaseModel):
    id: str
    handle: str
    display_name: str
    phone: str
    bio: str
    avatar_seed: int
    created_at: int

class UserPublic(BaseModel):
    id: str
    handle: str
    display_name: str
    bio: str
    avatar_seed: int

class UpdateProfile(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_seed: Optional[int] = None

class AddReaction(BaseModel):
    emoji: str

class ReactionOut(BaseModel):
    id: str
    message_id: str
    user_id: str
    emoji: str
    created_at: int

class AttachmentOut(BaseModel):
    id: str
    filename: str
    mime_type: str
    kind: str
    size: int
    url: str

class MessagePreview(BaseModel):
    id: str
    sender_id: str
    type: str
    body: Optional[str]
    created_at: int

class CardPreview(BaseModel):
    title: str
    subtitle: str

class SetPreview(BaseModel):
    title: str
    subtitle: str

class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    type: str
    body: Optional[str]
    attachment_id: Optional[str]
    attachment: Optional[AttachmentOut]
    reply_to_id: Optional[str]
    created_at: int
    reactions: List[ReactionOut] = []
    read_by: List[str] = []
    preview: Optional[CardPreview] = None

class ConversationOut(BaseModel):
    id: str
    other_user: UserPublic
    last_message: Optional[MessagePreview]
    unread_count: int
    created_at: int

class SendMessage(BaseModel):
    conversation_id: str
    type: str = "text"
    body: Optional[str] = None
    attachment_id: Optional[str] = None
    reply_to_id: Optional[str] = None
