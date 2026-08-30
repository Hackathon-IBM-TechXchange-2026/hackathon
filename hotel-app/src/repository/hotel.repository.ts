export type RoomType = 'SINGLE' | 'DOUBLE' | 'SUITE';
export type BookingStatus = 'PENDING' | 'CONFIRMED' | 'CANCELLED' | 'COMPLETED';

export interface Room {
  id: string;
  number: string;
  type: RoomType;
  pricePerNight: number;
  available: boolean;
}

export interface BookingRecord {
  id: string;
  guestId: string;
  roomId: string;
  checkIn: Date;
  checkOut: Date;
  status: BookingStatus;
  nights: number;
  baseRate: number;
  cleaningFee: number;
  total: number;
  metadata?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateBookingInput {
  guestId: string;
  roomId: string;
  checkIn: Date;
  checkOut: Date;
  nights: number;
  baseRate: number;
  cleaningFee: number;
  total: number;
  metadata?: Record<string, unknown>;
}

export class HotelRepository {
  private readonly rooms: Map<string, Room> = new Map();
  private readonly bookings: Map<string, BookingRecord> = new Map();
  private readonly guestIndex: Map<string, string[]> = new Map();

  async createRoom(room: Omit<Room, 'id'>): Promise<Room> {
    const id = `room_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const newRoom: Room = { ...room, id };
    this.rooms.set(id, newRoom);
    return newRoom;
  }

  async findRoomById(id: string): Promise<Room | null> {
    return this.rooms.get(id) || null;
  }

  async findAvailableRooms(type?: RoomType): Promise<Room[]> {
    const all = Array.from(this.rooms.values()).filter(r => r.available);
    return type ? all.filter(r => r.type === type) : all;
  }

  async updateRoomAvailability(id: string, available: boolean): Promise<Room> {
    const room = this.rooms.get(id);
    if (!room) throw new Error(`Room with id ${id} not found`);
    const updated: Room = { ...room, available };
    this.rooms.set(id, updated);
    return updated;
  }

  async createBooking(input: CreateBookingInput): Promise<BookingRecord> {
    const id = `booking_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const now = new Date();
    const record: BookingRecord = {
      ...input,
      id,
      status: 'CONFIRMED',
      createdAt: now,
      updatedAt: now,
    };
    this.bookings.set(id, record);

    const guestBookings = this.guestIndex.get(input.guestId) || [];
    guestBookings.push(id);
    this.guestIndex.set(input.guestId, guestBookings);

    return record;
  }

  async findBookingById(id: string): Promise<BookingRecord | null> {
    return this.bookings.get(id) || null;
  }

  async findBookingsByGuestId(guestId: string): Promise<BookingRecord[]> {
    const ids = this.guestIndex.get(guestId) || [];
    return ids.map(id => this.bookings.get(id)).filter((b): b is BookingRecord => b !== undefined);
  }

  async updateBookingStatus(id: string, status: BookingStatus): Promise<BookingRecord> {
    const booking = this.bookings.get(id);
    if (!booking) throw new Error(`Booking with id ${id} not found`);
    const updated: BookingRecord = { ...booking, status, updatedAt: new Date() };
    this.bookings.set(id, updated);
    return updated;
  }

  async countConfirmedBookings(guestId: string): Promise<number> {
    const bookings = await this.findBookingsByGuestId(guestId);
    return bookings.filter(b => b.status === 'CONFIRMED' || b.status === 'COMPLETED').length;
  }

  async clear(): Promise<void> {
    this.rooms.clear();
    this.bookings.clear();
    this.guestIndex.clear();
  }
}
