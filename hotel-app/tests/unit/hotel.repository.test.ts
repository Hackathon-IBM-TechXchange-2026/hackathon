import { HotelRepository, Room } from '../../src/repository/hotel.repository';

describe('HotelRepository', () => {
  let repository: HotelRepository;

  const BUILD_ROOM = (overrides: Partial<Omit<Room, 'id'>> = {}): Omit<Room, 'id'> => ({
    number: '101',
    type: 'SINGLE',
    pricePerNight: 150,
    available: true,
    ...overrides,
  });

  beforeEach(async () => {
    repository = new HotelRepository();
  });

  afterEach(async () => {
    await repository.clear();
  });

  // --- Room operations ---
  describe('createRoom', () => {
    it('should create a room and return it with an id', async () => {
      const room = await repository.createRoom(BUILD_ROOM());
      expect(room.id).toBeDefined();
      expect(room.id).toMatch(/^room_/);
      expect(room.type).toBe('SINGLE');
      expect(room.pricePerNight).toBe(150);
    });
  });

  describe('findRoomById', () => {
    it('should return the room when it exists', async () => {
      const created = await repository.createRoom(BUILD_ROOM());
      const found = await repository.findRoomById(created.id);
      expect(found).not.toBeNull();
      expect(found?.id).toBe(created.id);
    });

    it('should return null when room does not exist', async () => {
      const found = await repository.findRoomById('nonexistent');
      expect(found).toBeNull();
    });
  });

  describe('findAvailableRooms', () => {
    it('should return only available rooms', async () => {
      const r1 = await repository.createRoom(BUILD_ROOM({ available: true, number: '101' }));
      await repository.createRoom(BUILD_ROOM({ available: false, number: '102' }));
      const available = await repository.findAvailableRooms();
      expect(available.length).toBe(1);
      expect(available[0].id).toBe(r1.id);
    });

    it('should filter by room type', async () => {
      await repository.createRoom(BUILD_ROOM({ type: 'SINGLE', number: '101' }));
      await repository.createRoom(BUILD_ROOM({ type: 'SUITE', number: '201' }));
      const suites = await repository.findAvailableRooms('SUITE');
      expect(suites.length).toBe(1);
      expect(suites[0].type).toBe('SUITE');
    });
  });

  describe('updateRoomAvailability', () => {
    it('should update room availability', async () => {
      const room = await repository.createRoom(BUILD_ROOM({ available: true }));
      const updated = await repository.updateRoomAvailability(room.id, false);
      expect(updated.available).toBe(false);
    });

    it('should throw if room does not exist', async () => {
      await expect(repository.updateRoomAvailability('bad_id', false)).rejects.toThrow('not found');
    });
  });

  // --- Booking operations ---
  describe('createBooking', () => {
    it('should create a booking with CONFIRMED status', async () => {
      const room = await repository.createRoom(BUILD_ROOM());
      const checkIn = new Date('2025-12-01');
      const checkOut = new Date('2025-12-03');
      const booking = await repository.createBooking({
        guestId: 'guest_1',
        roomId: room.id,
        checkIn,
        checkOut,
        nights: 2,
        baseRate: 300,
        cleaningFee: 30,
        total: 330,
      });
      expect(booking.id).toMatch(/^booking_/);
      expect(booking.status).toBe('CONFIRMED');
      expect(booking.guestId).toBe('guest_1');
    });
  });

  describe('findBookingsByGuestId', () => {
    it('should return all bookings for a guest', async () => {
      const room = await repository.createRoom(BUILD_ROOM());
      await repository.createBooking({
        guestId: 'guest_1', roomId: room.id,
        checkIn: new Date('2025-12-01'), checkOut: new Date('2025-12-02'),
        nights: 1, baseRate: 150, cleaningFee: 30, total: 180,
      });
      await repository.createBooking({
        guestId: 'guest_1', roomId: room.id,
        checkIn: new Date('2025-12-05'), checkOut: new Date('2025-12-06'),
        nights: 1, baseRate: 150, cleaningFee: 30, total: 180,
      });
      const bookings = await repository.findBookingsByGuestId('guest_1');
      expect(bookings.length).toBe(2);
    });
  });

  describe('countConfirmedBookings', () => {
    it('should count CONFIRMED and COMPLETED bookings only', async () => {
      const room = await repository.createRoom(BUILD_ROOM());
      const b1 = await repository.createBooking({
        guestId: 'guest_2', roomId: room.id,
        checkIn: new Date('2025-11-01'), checkOut: new Date('2025-11-02'),
        nights: 1, baseRate: 150, cleaningFee: 30, total: 180,
      });
      await repository.createBooking({
        guestId: 'guest_2', roomId: room.id,
        checkIn: new Date('2025-11-05'), checkOut: new Date('2025-11-06'),
        nights: 1, baseRate: 150, cleaningFee: 30, total: 180,
      });
      await repository.updateBookingStatus(b1.id, 'CANCELLED');
      const count = await repository.countConfirmedBookings('guest_2');
      expect(count).toBe(1); // only the second one (CONFIRMED)
    });
  });

  describe('updateBookingStatus', () => {
    it('should update status correctly', async () => {
      const room = await repository.createRoom(BUILD_ROOM());
      const booking = await repository.createBooking({
        guestId: 'guest_3', roomId: room.id,
        checkIn: new Date('2025-12-01'), checkOut: new Date('2025-12-02'),
        nights: 1, baseRate: 150, cleaningFee: 30, total: 180,
      });
      const updated = await repository.updateBookingStatus(booking.id, 'COMPLETED');
      expect(updated.status).toBe('COMPLETED');
    });

    it('should throw if booking does not exist', async () => {
      await expect(repository.updateBookingStatus('bad_id', 'CANCELLED')).rejects.toThrow('not found');
    });
  });

  describe('clear', () => {
    it('should remove all rooms and bookings', async () => {
      await repository.createRoom(BUILD_ROOM());
      await repository.clear();
      const available = await repository.findAvailableRooms();
      expect(available.length).toBe(0);
    });
  });
});
